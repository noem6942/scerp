'''
accounting/connector_cash_ctrl_2.py
'''
import re
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from core.models import PersonBankAccount, PersonContact, PersonAddress
from scerp.mixins import get_translations, primary_language
from . import api_cash_ctrl, models
from .api_cash_ctrl import convert_to_xml, prepare_dict
from .api_cash_ctrl import PERSON_CATEGORY, TITLE


CASH_CTRL_FIELDS = [
    'c_id', 'c_created', 'c_created_by', 'c_last_updated', 'c_last_updated_by'
]
EXCLUDE_FIELDS = CASH_CTRL_FIELDS + [
    'id', 'tenant', 'sync_to_accounting', 'is_enabled_sync',
    'modified_at', 'modified_by', 'created_at', 'created_by',
    'is_protected', 'attachment', 'version',
    'last_received', 'message'
]


# helpers
def is_html(text):
    return bool(re.search(r'<[^>]+>', text))


def convert_text_to_html(text):        
    if text and not is_html(text):
        text = text.replace('\n', '<br>')
    return text    


class CashCtrl:
    api_class = None  # gets assigned with get, save or delete

    def __init__(self, model=None, language=None):
        self.language = language
        self.model = model  # needed for get and fields with custom
        self.api = None  # store later for further usage

    def _get_api(self, tenant):
        self.api = self.api_class(
            tenant.cash_ctrl_org_name,
            tenant.cash_ctrl_api_key,
            language=self.language
        )
        return self.api

    def _init_custom_fields(self, instance):
        '''
        returns a mapping dict for the model given, e.g.
        {
            'function': 'customField30',
            'hrm': 'customField31'
        }
        '''
        # Init
        custom_fields = getattr(self.model, 'CUSTOM', [])
        custom = {}

        # Parse fields
        for field_name, custom_field__code in custom_fields:
            # Get field instance
            custom_field = models.CustomField.objects.filter(
                tenant=instance.tenant, code=custom_field__code).first()

            # Assign
            if custom_field:
                custom[field_name] = custom_field.custom_field_key
            else:
                msg = f"custom field {custom_field__code} not existing."
                raise ValueError(msg)

        return custom

    def get_custom_field_tag(self, code):
        ''' return xml tag that can be sent to cashCtrl '''
        try:
            field = models.CustomField.objects.get(
                tenant=self.tenant, code=code)
            return f"customField{field.c_id}"
        except:
            raise ValueError(f"'{code}' not existing.")

    def get(self, tenant, created_by, params={}, overwrite_data=True,
            delete_not_existing=True, **filter_kwargs):
        api = self._get_api(tenant)
        data_list = api.list(params)
        c_ids = []

        for data in data_list:
            id = data['id']
            c_ids.append(id)

            # Get or create instances
            instance = self.model.objects.filter(tenant=tenant, c_id=id).first()
            if instance:
                if not overwrite_data:
                    continue  # no further update
            else:
                # create instance
                instance = self.model(
                    c_id=id,
                    tenant=tenant,
                    created_by=created_by
                )

            # add data
            for field in model_to_dict(instance, exclude=self.exclude):
                setattr(instance, field, data.get(field))

            if instance.is_inactive is None:
                instance.is_inactive = False

            # save instance
            if getattr(self, 'save_download', None):
                # Individual saving
                self.save_download(instance, data)

            # Default saving
            instance.sync_to_accounting = False
            instance.save()

        if delete_not_existing:
            self.model.objects.filter(
                ~Q(tenant=tenant), ~Q(c_id__in=c_ids), c_id__isnull=False
            ).delete()

    def reload(self, instance):
        data = self.api.read(instance.c_id)
        for key, value in data.items():
            if key == 'id':
                continue
            elif key in CASH_CTRL_FIELDS + self.reload_keys:
                setattr(instance, key, value)

    def save(self, instance, created=None):
        # Check if read only
        if getattr(self, 'read_only', False):
            raise ValueError('cashCtrl, read only entity. Only code saved.')

        # Get api
        api = self._get_api(instance.tenant)

        # Prepare data
        data = model_to_dict(instance, exclude=self.exclude)

        # Add custom data
        custom = self._init_custom_fields(instance)
        if custom:
            data['custom'] = {
                key_cash_ctrl: data.pop(field_name, None)
                for field_name, key_cash_ctrl in custom.items()
            }

        # Individualize data
        if getattr(self, 'adjust_for_upload', None):
            self.adjust_for_upload(instance, data, created)

        # Save
        if created or not instance.c_id:
            # Save object
            response = api.create(data)
            instance.c_id = response.get('insert_id')
            instance.sync_to_accounting = False

            # Read new instance if necessary
            reload_keys = getattr(self, 'reload_keys', [])
            if reload_keys:
                self.reload(instance)

            # Save
            update_fields = CASH_CTRL_FIELDS + reload_keys
            instance.save(
                update_fields=['c_id', 'sync_to_accounting'] + reload_keys)
        else:
            data['id'] = instance.c_id
            _response = api.update(data)

        if getattr(self, 'post_save', None):
            self.post_save(instance)

    def delete(self, instance):
        api = self._get_api(instance.tenant)
        if instance.c_id:
            response = api.delete(instance.c_id)
            return response
        return None


class CustomFieldGroup(CashCtrl):
    api_class = api_cash_ctrl.CustomFieldGroup
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def get(self, tenant, created_by, params={}, update=True):
        for field in api_cash_ctrl.FIELD_TYPE:
            params = {'type': field.value}
            super().get(tenant, created_by, params, update)

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"


class CustomField(CashCtrl):
    api_class = api_cash_ctrl.CustomField
    exclude = EXCLUDE_FIELDS + ['code', 'group_ref', 'notes', 'is_inactive']

    def get(self, tenant, created_by, params={}, update=True):
        for field in api_cash_ctrl.FIELD_TYPE:
            params = {'type': field.value}
            super().get(tenant, created_by, params, update)

    def adjust_for_upload(self, instance, data, created=None):
        # Get foreign c_ids
        data['type'] = instance.group.type
        data['group_id'] = instance.group.c_id

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"
        instance.group = models.CustomFieldGroup.objects.get(c_id=data['id'])


class FileCategory(CashCtrl):
    api_class = api_cash_ctrl.FileCategory
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"


class Location(CashCtrl):
    api_class = api_cash_ctrl.Location
    exclude = EXCLUDE_FIELDS + ['notes', 'is_inactive']


class FiscalPeriod(CashCtrl):
    api_class = api_cash_ctrl.FiscalPeriod
    exclude = EXCLUDE_FIELDS + ['notes', 'is_inactive']


class Currency(CashCtrl):
    api_class = api_cash_ctrl.Currency
    exclude = EXCLUDE_FIELDS + ['notes', 'is_inactive']


class SequenceNumber(CashCtrl):
    api_class = api_cash_ctrl.SequenceNumber
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']


class Unit(CashCtrl):
    api_class = api_cash_ctrl.Unit
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def get(self, *args, **kwargs):
        raise ValueError("Units are only edited in scerp")


class CostCenterCategory(CashCtrl):
    api_class = api_cash_ctrl.AccountCostCenterCategory
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def adjust_for_upload(self, instance, data, created=None):
        data['parent_id'] = instance.parent.c_id if instance.parent else None

    def save_download(self, instance, data):
        instance.parent = models.CostCenterCategory.objects.filter(
            c_id=data['parent_id']).first()


class CostCenter(CashCtrl):
    api_class = api_cash_ctrl.AccountCostCenter
    exclude = EXCLUDE_FIELDS

    def adjust_for_upload(self, instance, data, created=None):
        if instance.category:
            data['category_id'] = instance.category.c_id

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"
        instance.category = models.CostCenterCategory.objects.filter(
            c_id=data['category_id']).first()


class AccountCategory(CashCtrl):
    api_class = api_cash_ctrl.AccountCategory
    exclude = EXCLUDE_FIELDS + ['is_inactive', 'notes']

    @staticmethod
    def add_numbers(name, number):
        if number:
            return f"{int(number)} {name}"
        return name

    @staticmethod
    def skip_numbers(name):
        if name and ' ' in name:
            number, text = name.split(' ', 1)
            if number.isnumeric():
                return text
        return name

    def adjust_for_upload(self, instance, data, created=None):
        # parent_id
        data['parent_id'] = (
            instance.parent.c_id if instance.parent else None)

        # name, encode numbers in headings
        if instance.tenant.encode_numbers and not instance.is_top_level_account:
            # Add numbers
            data['name'] = {
                language: self.add_numbers(value, data['number'])
                for language, value in data['name'].items()
            }

    def save_download(self, instance, data):
        # parent
        instance.parent = models.AccountCategory.objects.filter(
            c_id=data['parent_id']).first()

        # decode name
        if instance.tenant.encode_numbers:
            # Skip numbers
            if type(instance.name) == dict:
                name_dict = {
                    language: self.skip_numbers(value)
                    for language, value in instance.name.items()
                }
                instance.name = name_dict


class Account(CashCtrl):
    api_class = api_cash_ctrl.Account
    exclude = EXCLUDE_FIELDS

    def adjust_for_upload(self, instance, data, created=None):
        # category_id
        data['category_id'] = (
            instance.category.c_id if instance.category else None)

        # currency_id
        data['currency_id'] = (
            instance.currency.c_id if instance.currency else None)

        # allocations
        allocations = models.Allocation.objects.filter(account__id=instance.id)
        data['allocations'] = [{
            'share': float(allocation.share),
            'toCostCenterId': allocation.to_cost_center.c_id,
        } for allocation in allocations.all()]

        # tax_id
        data.pop('tax_c_id', None)

    def save_download(self, instance, data):
        # category
        instance.category = models.AccountCategory.objects.filter(
            c_id=data['category_id']).first()


class BankAccount(CashCtrl):
    api_class = api_cash_ctrl.AccountBankAccount
    exclude = EXCLUDE_FIELDS + ['account', 'code', 'notes']
    read_only = True

    def adjust_for_upload(self, instance, data, created=None):
        # account_id
        data['account_id'] = (
            instance.account.c_id if instance.account else None)

        # currency_id
        data['currency_id'] = (
            instance.currency.c_id if instance.currency else None)

    def save_download(self, instance, data):
        # account
        instance.account = models.Account.objects.filter(
            c_id=data['account_id']).first()

        if not instance.code:
            instance.code = f"custom {data['id']}"


class Tax(CashCtrl):
    api_class = api_cash_ctrl.Tax
    exclude = EXCLUDE_FIELDS + ['code' + 'is_inactive', 'notes']

    def adjust_for_upload(self, instance, data, created=None):
        # account_id
        data['account_id'] = (
            instance.account.c_id if instance.account else None)

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"

        # account
        instance.account = models.Account.objects.filter(
            c_id=data['account_id']).first()


class Rounding(CashCtrl):
    api_class = api_cash_ctrl.Rounding
    exclude = EXCLUDE_FIELDS + ['code' + 'is_inactive', 'notes']

    def adjust_for_upload(self, instance, data, created=None):
        # account_id
        data['account_id'] = (
            instance.account.c_id if instance.account else None)

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"

        # account
        instance.account = models.Account.objects.filter(
            c_id=data['account_id']).first()


class Setting(CashCtrl):
    api_class = api_cash_ctrl.Setting
    exclude = EXCLUDE_FIELDS + ['code' + 'is_inactive', 'notes']

    def save(self, instance, created=None):
        raise ValueError("Currently no save of Settings")

    def get(self, tenant, created_by, params={}, update=True):
        api = self._get_api(tenant)
        data = api.read()
        data['id'] = 1  # enforce settings to have an id
        data = {k.lower(): v for k, v in data.items()}  # convert cases

        if update:
            db_op = self.model.objects.update_or_create
        else:
            db_op = self.model.objects.get_or_create

        obj, created = db_op(
            tenant=tenant, c_id=data.pop('id'), defaults=dict(
                created_by=created_by,
                data=data
            )
        )


class OrderLayout(CashCtrl):
    api_class = api_cash_ctrl.OrderLayout
    exclude = EXCLUDE_FIELDS + ['' + 'notes']


class OrderCategory(CashCtrl):
    api_class = api_cash_ctrl.OrderCategory
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive', 'status_data']
    abstract = True

    def make_base(self, instance, data, created):
        ''' make data base for Order Categories '''
        # type
        order_type = instance.type
        if not isinstance(order_type, str):
            order_type = order_type.value

        data.update({
            'type': order_type,
            'book_type': instance.book_type,
            'is_display_item_gross': instance.is_display_item_gross
        })

        # Order layout
        if instance.layout:
            data['layout_id'] = instance.layout.c_id

        if instance.sequence_number:
            data['sequence_nr_id'] = instance.sequence_number.c_id

    def save(self, instance, created=None):
        '''
        Order Category needs reload status after save. This is why we define
        here our own save()
        '''
        super().save(instance, created)

        # get the full record to update status
        instance.refresh_from_db()
        data = self.api.read(instance.c_id)
        instance.status_data = data['status']
        instance.book_template_data = data['book_templates']

        # save
        instance.sync_to_accounting = False
        instance.save()


class OrderCategoryContract(OrderCategory):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data, created)
        data['account_id'] = instance.account.c_id

        # status, we only use minimal values as no booking with contracts
        if created:
            data['status'] = [{
                'icon': instance.COLOR_MAPPING[status],
                'name': convert_to_xml(
                    get_translations(force_str(status.label))),
            } for status in self.model.STATUS]
        else:
            data['status'] = instance.status_data


class OrderCategoryIncoming(OrderCategory):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data, created)

        # accounts
        data['account_id'] = instance.credit_account.c_id
        bank_account = instance.bank_account.c_id

        # status, we only use minimal values as we do the booking ourselves
        STATUS = instance.STATUS
        data['status'] = [{
            'icon': instance.COLOR_MAPPING[status],
            'name': convert_to_xml(
                get_translations(force_str(status.label))),
            'isBook': instance.BOOKING_MAPPING[status]
        } for status in STATUS]

        # BookTemplates
        # booking
        booking = {
            'accountId': data['account_id'],
            'name': convert_to_xml(get_translations('Booking')),
            'isAllowTax': False,  # no --> we specify tax in the item
        }

        # payment
        payment_account = instance.bank_account
        if payment_account.account and payment_account.account.c_id:
            payment = {
                'accountId': payment_account.account.c_id,
                'name': convert_to_xml(get_translations('Payment'))
            }
        else:
            raise ErrorValue("Bank account has no booking account assigned")

        # assign
        data['book_templates'] = [booking, payment]

        # Rounding
        if getattr(instance, 'rounding', None):
            data['rounding_id'] = instance.rounding.c_id


class OrderCategoryOutgoing(OrderCategory):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data, created)

        # accounts
        data['account_id'] = instance.debit_account.c_id
        bank_account = instance.bank_account.c_id

        # status, we only use minimal values as we do the booking ourselves
        STATUS = instance.STATUS
        data['status'] = [{
            'icon': instance.COLOR_MAPPING[status],
            'name': convert_to_xml(
                get_translations(force_str(status.label))),
            'isBook': instance.BOOKING_MAPPING[status]
        } for status in STATUS]

        # BookTemplates
        # booking
        booking = {
            'accountId': data['account_id'],
            'name': convert_to_xml(get_translations('Booking')),
            'isAllowTax': False,  # specify with order items
        }

        # payment
        payment_account = instance.bank_account
        if payment_account.account and payment_account.account.c_id:
            payment = {
                'accountId': payment_account.account.c_id,
                'name': convert_to_xml(get_translations('Payment'))
            }
        else:
            raise ValueError("Bank account has no booking account assigned")

        # assign
        data['book_templates'] = [booking, payment]

        # Rounding
        if getattr(instance, 'rounding', None):
            data['rounding_id'] = instance.rounding.c_id


class Order(CashCtrl):
    api_class = api_cash_ctrl.Order
    exclude = EXCLUDE_FIELDS
    reload_keys = ['nr']
    abstract = True

    def make_base(self, instance, data):
        # Category, person
        data['category_id'] = instance.category.c_id
        if instance.responsible_person:
            person = instance.responsible_person
            data['responsible_person_id'] = person.c_id if person else None

        # model is in [OrderCategoryIncoming, OrderCategoryOutgoing]
        category_model = instance.category._meta.model

        # Get status
        for index, status in enumerate(category_model.STATUS):
            if instance.status == status:
                break
        data['status_id'] = instance.category.status_data[index]['id']


class OrderContract(Order):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data)

        # associate
        person = instance.associate
        if not person or not person.c_id:
            raise ValueError("OrderContract: No associate.id given.")
        data['associate_id'] = person.c_id

        # description
        if instance.description:
            description = instance.description
        else:
            description = f'Order from {instance.date}'
            data['description'] = description

        # Create one item with total price
        data['items'] = [{
            'accountId': instance.category.account.c_id,
            'name': description,
            'unitPrice': float(instance.price_excl_vat)
        }]


class BookEntry(CashCtrl):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data)

        # associate
        if instance.associate:
            person = instance.associate
            data['associate_id'] = person.c_id if person else None

        # Create one item with total price
        data['items'] = [{
            'accountId': instance.category.account.c_id,
            'name': instance.description,
            'unitPrice': float(instance.price_excl_vat)
        }]


class IncomingOrder(Order):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data)

        # associate
        if instance.contract.associate:
            person = instance.contract.associate
            data['associate_id'] = person.c_id if person else None

        # Create one item with total price
        category = instance.category
        bank_account = PersonBankAccount.objects.filter(
            tenant=instance.tenant,
            person=instance.contract.associate,
            type=PersonBankAccount.TYPE.DEFAULT
        ).first()

        if not bank_account:
            raise ValueError(_("No bank account for creditor specified."))

        data['items'] = [{
            'accountId': instance.category.expense_account.c_id,
            'name': instance.description,
            'description': (
                f"{PersonBankAccount._meta.verbose_name}: "
                f"{bank_account.bic}, {bank_account.iban}"),
            'unitPrice': float(instance.price_incl_vat),
            'taxId': category.tax.c_id if category.tax else None
        }]

        # Rounding
        if getattr(instance.category, 'rounding', None):
            data['rounding_id'] = instance.category.rounding.c_id

        # Due days
        if getattr(instance, 'due_days', None):
            data['due_days'] = instance.due_days

    def upload_attachment(self, instance):
        '''
        Attach file, currently not in use
        '''
        # get the full record to update status
        for attachment in instance.attachments.all():
            # upload file
            conn = api_cash_ctrl.File(
                instance.tenant.cash_ctrl_org_name,
                instance.tenant.cash_ctrl_api_key)
            data = {
                'name': attachment.file.name,
                'category_id': 1,
            }
            file_id, _path = conn.upload(attachment.file.path, data)

            # update OrderDocument
            conn = api_cash_ctrl.OrderDocument(
                instance.tenant.cash_ctrl_org_name,
                instance.tenant.cash_ctrl_api_key)
            document = self.api.read(instance.c_id)
            document['file_id'] = file_id
            response = conn.update(document)


class OutgoingOrder(Order):
    exclude = EXCLUDE_FIELDS + ['recipient_address']

    @staticmethod
    def correct_cash_ctrl_article_price(item):
        ''' 
        should be:
        return float(item.article.sales_price)
        but cashCtrl  interpretes bruttopreise as nettopreis
        '''
        tax_factor = (
            1 + item.article.category.tax.percentage / 100
        ) if item.article.category.tax else 1
        return float(item.article.sales_price * tax_factor)

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data)

        # category, associate
        data.update({
            'category': instance.category.c_id,
            'associate_id': instance.associate.c_id
        })

        # currency
        if instance.category.currency:
            data['currency_id'] = instance.category.currency.c_id

        # responsible_person
        if instance.category.responsible_person:
            person = instance.category.responsible_person
        elif instance.responsible_person:
            person = instance.responsible_person
        else:
            person = None

        if person:
            data['responsible_person_id'] = person.c_id

        # Create items from articles
        queryset_items = models.OutgoingItem.objects.filter(
            order=instance).order_by('id')
        if not queryset_items:
            raise ValueError('No items in order')
        
        # Tax
        
        # Check sales account
        for item in queryset_items.all():
            if not item.article.category.sales_account:
                raise ValueError(f"No account defined for {item.article}")

        # Fill in items
        data['items'] = [{
            'accountId': item.article.category.sales_account.c_id,
            'name': primary_language(item.article.name),
            'description': primary_language(item.article.description),
            'quantity': float(item.quantity),
            'unitPrice': self.correct_cash_ctrl_article_price(item),
            'unitId': item.article.unit.c_id,
            'taxId': (
                item.article.category.tax.c_id
                if item.article.category.tax else None
            ),
        } for item in queryset_items.all()]

        # Rounding
        if getattr(instance.category, 'rounding', None):
            data['rounding_id'] = instance.category.rounding.c_id

        # Due days
        data['due_days'] = (
            instance.due_days if getattr(instance, 'due_days', None)
            else instance.category.due_days
        )

    def post_save(self, instance):
        # get and update order document
        conn = api_cash_ctrl.OrderDocument(
            instance.tenant.cash_ctrl_org_name,
            instance.tenant.cash_ctrl_api_key)
        document = self.api.read(instance.c_id)

        # get location
        location = instance.contract.category.org_location
        org_address = (
            f'{location.address}\n'
            f'{location.zip} {location.city}')

        # get recipient data
        bank_account = instance.category.bank_account

        # layout
        header = (
            instance.header if instance.header
            else instance.category.header)
        footer = (
            instance.footer if instance.footer
            else instance.category.footer)

        # update document
        document.update({
            'org_location_id': location.c_id,
            'org_address': org_address,
            'org_bank_account_id': bank_account.c_id,            
            'header': convert_text_to_html(instance.header),
            'footer': convert_text_to_html(instance.contract.category.footer)
        })

        # update address
        if instance.recipient_address:
            document.update({
                'recipient_address': instance.recipient_address,
                'recipient_address_id': None
            })

        response = conn.update(document)

'''
class IncomingBookEntry(CashCtrl):
    api_class = api_cash_ctrl.OrderBookEntry
    exclude = EXCLUDE_FIELDS + ['notes', 'is_inactive']

    def adjust_for_upload(self, instance, data, created=None):
        order = instance.order
        category = order.category
        data.update({
            'order_ids': [order.c_id],
            'amount': order.price_incl_vat,
            'account_id': category.bank_account.c_id,
            'tax_id': category.tax.c_id
        })

        if category.currency:
            data['currency_id'] = category.currency.c_id
'''

class AssetCategory(CashCtrl):
    api_class = api_cash_ctrl.AssetCategory
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive', 'unit']

    def get(self, *args, **kwargs):
        raise ValueError("AssetCategory are only edited in scerp")


class Asset(CashCtrl):
    api_class = api_cash_ctrl.Asset
    exclude = EXCLUDE_FIELDS + [
        'code', 'status', 'warranty_months', 'number', 'serial_number',
        'tag', 'registration_number', 'batch', 'attachments'
    ]
    reload_keys = ['nr']

    def adjust_for_upload(self, instance, data, created=None):
        # Prepare category_id
        if getattr(instance, 'category', None):
            data['category_id'] = instance.category.c_id


class ArticleCategory(CashCtrl):
    api_class = api_cash_ctrl.ArticleCategory
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def adjust_for_upload(self, instance, data, created=None):
        # Prepare parent_id
        if getattr(instance, 'parent', None):
            data['parent_id'] = instance.parent.c_id

        # Prepare purchase_account
        if getattr(instance, 'purchase_account', None):
            data['purchase_account_id'] = instance.purchase_account.c_id

        # Prepare sales_account
        if getattr(instance, 'sales_account', None):
            data['sales_account'] = instance.sales_account.c_id

        # Prepare sequence_nr
        if getattr(instance, 'sequence_nr', None):
            data['sequence_nr_id'] = instance.sequence_nr.c_id

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"


class Article(CashCtrl):
    api_class = api_cash_ctrl.Article
    exclude = EXCLUDE_FIELDS + ['tax']
    reload_keys = ['nr']

    def adjust_for_upload(self, instance, data, created=None):
        # Prepare category_id
        if getattr(instance, 'category', None):
            data['category_id'] = instance.category.c_id

        # Prepare currency
        if getattr(instance, 'currency', None):
            data['currency_id'] = instance.currency.c_id

        # Prepare location
        if getattr(instance, 'location', None):
            data['location_id'] = instance.location.c_id

        # Prepare sequence_nr
        if getattr(instance, 'sequence_nr', None):
            data['sequence_nr_id'] = instance.sequence_nr.c_id

        # Prepare unit
        if getattr(instance, 'unit', None):
            data['unit_id'] = instance.unit.c_id


# CashCtrlDual
class Title(CashCtrl):
    api_class = api_cash_ctrl.PersonTitle
    exclude = EXCLUDE_FIELDS + ['code']

    def get(self, *args, **kwargs):
        raise ValueError("Titles are only edited in scerp")


class PersonCategory(CashCtrl):
    api_class = api_cash_ctrl.PersonCategory
    exclude = EXCLUDE_FIELDS + ['code']

    def get(self, *args, **kwargs):
        raise ValueError("Person Categories are only edited in scerp")


class Person(CashCtrl):
    api_class = api_cash_ctrl.Person
    exclude = EXCLUDE_FIELDS + ['photo']  # for now
    reload_keys = ['nr']

    @staticmethod
    def make_address(addr):
        # Base
        data = {
            'type': addr.type,
            'city': addr.address.city,
            'zip': addr.address.zip,
            'country': addr.address.country.alpha3,
        }

        # Individual
        if addr.type == PersonAddress.TYPE.INVOICE:
            # address
            praefix = (
                addr.post_office_box + '\n' if addr.post_office_box else '')

            # use additional_information for company
            data.update(prepare_dict({
                'company': addr.additional_information,
                'address': praefix + addr.address.address,
                'is_hide_name': True
            }))
        else:
            # add post_office_box and additional_information
            data['address'] = addr.address_full

        return data

    @staticmethod
    def make_contact(contact):
        return {
            'type': contact.type,
            'address': contact.address
        }

    @staticmethod
    def make_bank_account(account):
        return {
            'type': account.type,
            'iban': account.iban,
            'bic': account.bic
        }

    def adjust_for_upload(self, instance, data, created=None):
        # Make data

        # Category
        if getattr(instance, 'category', None):
            data['category_id'] = instance.category.c_id

        # superior
        if getattr(instance, 'superior', None):
            data['category_id'] = instance.superior.c_id

        # Add Title
        if getattr(instance, 'title', None):
            data['title_id'] = instance.title.c_id

        # Make Bank accounts
        bank_accounts = PersonBankAccount.objects.filter(person=instance)
        data['bank_accounts'] = [
            self.make_bank_account(account)
            for account in bank_accounts.order_by('id')
        ]

        # Make contacts
        contacts = PersonContact.objects.filter(person=instance)
        data['contacts'] = [
            self.make_contact(contact)
            for contact in contacts.order_by('id')
        ]

        # Make addresses
        addresses = PersonAddress.objects.filter(person=instance)
        data['addresses'] = [
            self.make_address(addr)
            for addr in addresses.order_by('id')
        ]

    def get(self, *args, **kwargs):
        raise ValueError("Persons are only edited in scerp.")
