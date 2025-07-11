'''
accounting/mixins.py

helpers for models.py and signals.py
general helpers not related to cash_ctrl
pylint checked 2024-12-25
'''
from django.utils.translation import get_language, gettext_lazy as _

from scerp.mixins import COPY, SafeDict
from .models import OutgoingItem

DIGITS_FUNCTIONAL = 4, 0
DIGITS_ACCOUNT = 5, 2


# AccountPositionAbstract
def format_number_with_leading_digits(praefix_digits, num, length, comma):
    '''return a string like f"{praefix_digits}{int_str}{dec_str}"
    '''
    # Format the number with the required decimal places
    formatted_num = f"{num:.{comma}f}"

    # Remove the decimal point and pad the number with leading zeros if necessary
    if comma:
        int_part, dec_part = formatted_num.split(".")
    else:
        int_part, dec_part = formatted_num, None

    # assemble
    int_str = int_part.zfill(length)
    dec_str = '' if dec_part is None else f".{dec_part}"

    # Combine the prefix digit with the integer and decimal parts
    return f"{praefix_digits}{int_str}{dec_str}"


def account_position_calc_number(
        account_type, function, account_number, is_category):
    '''calc number with pattern:
        AFFFFCNNNNN.NN
        A .. ACCOUNT_TYPE
        FFFF .. function with leading zeros,
        C .. 1 if is_category else 0
        NNNNN.NN .. account number with leading zeros and 2 commas

        ff in account_number is ignored (replace by '')
    '''
    # Clean function
    try:
        function = 0 if function is None else int(function)
    except ValueError:
        function = 0

    # Eliminate ff
    if account_number:
        account_number = account_number.replace('ff', '').strip()

    # Calc prafix, i.e.{type_1}{function_4}
    praefix = format_number_with_leading_digits(
        account_type, function, *DIGITS_FUNCTIONAL)

    # Add category flag
    praefix += '1' if is_category else '0'

    # clean account_number
    try:
        account_number = float(account_number)
    except ValueError:
        account_number = 0

    # Fill in number
    number = format_number_with_leading_digits(
        praefix, account_number, *DIGITS_ACCOUNT)

    return float(number)


class AccountPositionCheck():
    '''AccountPosition Checks
    '''
    def __init__(self, query_positions):
        query_positions = query_positions.order_by(
            'function', '-is_category', 'account_number')
        # Check levels
        self.positions = [x for x in query_positions]

    def get_parent(self, position):
        # Init
        level_check = position.level - 1
        nr = self.positions.index(position)

        # Check
        for pos in reversed(self.positions[:nr]):
            if position.is_category:
                c1 = pos.account_number[:level_check]
                c2 = position.account_number[:level_check]
                if c1 == c2:
                    return pos
            elif pos.function == position.function:
                return pos
            else:
                print("*", pos.function, position.function)
        return None

    def check(self):
        # Check is only upper
        for position in self.positions:
            if position.name.isupper():
                msg = _("'{number} {name}' only contains upper letters").format(
                    number=position.account_number, name=position.name)
                raise ValueError(msg)

        # Check if every position has a parent
        for position in self.positions:
            if position == self.positions[0]:
                if position.level != 1:
                    raise ValueError(_("Positions not starting with level 1"))
            elif not self.get_parent(position):
                msg = _("Positions '{number} {name}' has no parents").format(
                    number=position.account_number, name=position.name)
                raise ValueError(msg)
        return True

    def convert_upper_case(self):
        change_list = []
        for position in self.positions:
            if position.name.isupper():
                position.name = position.name.title()
                position.save()
                change_list.append(position)

        return change_list


def _make_unique_nr(instance):
    if not getattr(instance, 'nr', None):
        return

    model = instance.__class__

    base_nr = instance.nr
    if model == Article:
        # Look for existing similar numbers like 'ABC', 'ABC-COPY', 'ABC-COPY-2', etc.
        existing = model.objects.filter(
            nr__startswith=base_nr).values_list('nr', flat=True)
        existing_set = set(existing)

        if base_nr not in existing_set:
            return  # no conflict

        # Try incrementing suffixes
        counter = 1
        new_nr = f"{base_nr}-COPY"
        while new_nr in existing_set:
            counter += 1
            new_nr = f"{base_nr}-COPY-{counter}"

        instance.nr = new_nr
    else:
        instance.nr = None


def copy_entity(instance):
    ''' copy an accounting instance
    '''    
    instance = queryset.first()

    # Init
    fields_none = [
        'pk', 'modified_at', 'created_at', 'c_id', 'last_received'
    ]
    for field in fields_none:
        setattr(instance, field, None)
    instance.sync_to_accounting = True

    # Copy fields
    fields = [
        'code', 'name', 'name_singular', 'name_plural'
    ]
    for field in fields:
        attr = getattr(instance, field, None)
        if isinstance(attr, dict):
            for lang, value in attr.items():
                attr[lang] += COPY
        elif isinstance(attr, str):
            setattr(instance, field, attr + COPY)

    # 'nr'
    if getattr(instance, 'nr', None):
        if model == Article:
            _make_unique_nr(instance)
        else:
            instance.nr = None

    # save
    instance.save()


def make_installment_payment(
        order, user, nr_of_installments, date, header, due_days, 
        fee_quantity=None, due_days_first=None):
    ''' make installment payments
    '''
    # Check nr_of_installments
    if nr_of_installments < 2:
        raise ValueError("Enter at least 2 installments.")

    # Get Outgoing Items
    outgoing_items = OutgoingItem.objects.filter(
        order=order).order_by('id')

    # Get due date    
    if not due_days_first:
        due_days_first = due_days

    # Make copies
    for nr in range(1, nr_of_installments + 1):
        # Prepare duplicate by fetching fresh copy or cloning again
        order_new = order.__class__.objects.get(pk=order.pk)
        # copy and init
        fields_none = [
            'pk', 'modified_at', 'created_at', 'c_id', 'last_received',
            'nr'
        ]
        for field in fields_none:
            setattr(order_new, field, None)

        # header
        template = header.format_map(SafeDict(
            nr=nr,
            total=nr_of_installments,
            invoice_nr=order.nr
        ))
        order_new.header = template + '<br>' + order_new.header
        order_new.description = order_new.description + '; ' + template

        # discount
        discount = discount_percentage = 100 - 100 / nr_of_installments

        # others
        order_new.date = date
        order_new.due_days = due_days_first + due_days * (nr - 1)
        order_new.save()

        # Copy outgoingItem
        for item in outgoing_items:
            obj = OutgoingItem.objects.create(
                tenant=order.tenant,
                created_by=user,
                article=item.article,
                quantity=item.quantity,
                discount_percentage=discount,
                order=order_new
            )

        # Installment Fee
        if fee_quantity:
            article = order.category.installment_article
            obj = OutgoingItem.objects.create(
                tenant=order.tenant,
                created_by=user,
                article=article,
                quantity=fee_quantity,
                discount_percentage=0,
                order=order_new
            )

    # Update old    
    disclaimer = _('Replaced by {count} installment payments').format(
        count=nr_of_installments)
    order.description += "; " + disclaimer
    order.header = disclaimer + '<br>' + order.header
    order.discount_percentage = 100
    order.sync_to_accounting = True
    order.save()
