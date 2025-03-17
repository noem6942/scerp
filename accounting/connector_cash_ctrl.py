'''
accounting/connector_cash_ctrl_2.py
'''
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.encoding import force_str

from core.models import PersonBankAccount, PersonContact, PersonAddress
from scerp.mixins import get_translations
from . import api_cash_ctrl, models
from .api_cash_ctrl import clean_dict, convert_to_xml


CASH_CTRL_FIELDS = [
    'c_id', 'c_created', 'c_created_by', 'c_last_updated', 'c_last_updated_by'
]
EXCLUDE_FIELDS = CASH_CTRL_FIELDS + [
    'id', 'tenant', 'sync_to_accounting', 'is_enabled_sync',
    'modified_at', 'modified_by', 'created_at', 'created_by',
    'is_protected', 'attachment', 'version',
    'setup', 'last_received', 'message'
]


class CashCtrl:
    api_class = None  # gets assigned with get, save or delete

    def __init__(self, model=None, language=None):
        self.language = language
        self.model = model  # needed for get and fields with custom
        self.api = None  # store later for further usage

    def _get_api(self, setup):
        self.api = self.api_class(
            setup.org_name, setup.api_key, language=self.language)
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
                setup=instance.setup, code=custom_field__code).first()

            # Assign
            if custom_field:
                custom[field_name] = custom_field.custom_field_key
            else:
                msg = f"custom field {custom_field__code} not existing."
                raise ValueError(msg)

        return custom

    def get(self, setup, created_by, params={}, overwrite_data=True,
            delete_not_existing=True):
        api = self._get_api(setup)
        data_list = api.list(params)
        c_ids = []

        for data in data_list:
            id = data['id']
            c_ids.append(id)

            # Get or create instances
            instance = self.model.objects.filter(setup=setup, c_id=id).first()
            if instance:
                if not overwrite_data:
                    continue  # no further update
            else:
                # create instance
                instance = self.model(
                    c_id=id,
                    tenant=setup.tenant,
                    setup=setup,
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
                ~Q(setup=setup), ~Q(c_id__in=c_ids), c_id__isnull=False
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
        api = self._get_api(instance.setup)

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
            update_fields = CASH_CTRL_FIELDS + reload_keys
            instance.save(
                update_fields=['c_id', 'sync_to_accounting'] + reload_keys)
        else:
            data['id'] = instance.c_id
            _response = api.update(data)

    def delete(self, instance):
        api = self._get_api(instance.setup)
        if instance.c_id:
            response = api.delete(instance.c_id)
            return response
        return None


class CashCtrlDual(CashCtrl):

    def __init__(self, model=None, language=None):
        super().__init__(model, language)
        self.instance_acct = None  # gets assigned in save

    def reload(self, instance):
        data = self.api.read(instance.c_id)
        for key, value in data.items():
            if key == 'id':
                continue
            elif key in CASH_CTRL_FIELDS + self.reload_keys:
                setattr(instance, key, value)

    def save(self, instance, created=None):
        # Get setup
        self.instance_acct = self.model_accounting.objects.filter(
                tenant=instance.tenant, core=instance).first()
        if self.instance_acct:
            setup = self.instance_acct.setup       
        else:
            # instance_acct not existing yet
            setup = models.APISetup.get_setup(tenant=instance.tenant)            

        # Get api
        api = self._get_api(setup)

        # Prepare data
        data = model_to_dict(instance, exclude=self.exclude)
        if getattr(self, 'adjust_for_upload', None):
            self.adjust_for_upload(instance, data, created)

        # Save
        if not self.instance_acct or not self.instance_acct.c_id:
            # Save object
            response = api.create(data)
            c_id = response.get('insert_id')
            self.instance_acct = self.model_accounting.objects.create(
                core=instance,
                c_id=c_id,
                tenant=instance.tenant,
                setup=setup,
                created_by=instance.tenant.created_by
            )          
            if getattr(self, 'reload_keys', []):
                self.reload(self.instance_acct)
        else:
            data['id'] = self.instance_acct.c_id
            _response = api.update(data)

        # Only updates this field, avoids triggering full post_save
        instance.sync_to_accounting = False
        instance.save(update_fields=['sync_to_accounting'])

    def get(self, model_accounting, setup, created_by, update=True):
        api = self._get_api(setup)
        data_list = api.list()

        for data in data_list:
            # Get or create instances
            instance_acct = model_accounting.objects.filter(
                setup=setup, c_id=data['id']).first()
            if instance_acct:
                if update:
                    instance = instance_acct.core  # assign instance
                else:
                    continue  # no further update
            else:
                # create instance
                instance = self.model(
                    tenant=setup.tenant,
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
            
            instanc.sync_to_accounting = False
            instance.save()            
            
            # save instance_acct
            if not instance_acct:
                # create accounting_instance
                instance_acct = model_accounting(
                    core=instance,
                    c_id=data['id'],
                    tenant=setup.tenant,
                    setup=setup,
                    created_by=created_by
                )


class CustomFieldGroup(CashCtrl):
    api_class = api_cash_ctrl.CustomFieldGroup
    exclude = EXCLUDE_FIELDS + ['code', 'notes', 'is_inactive']

    def get(self, setup, created_by, params={}, update=True):
        for field in api_cash_ctrl.FIELD_TYPE:
            params = {'type': field.value}
            super().get(setup, created_by, params, update)

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"


class CustomField(CashCtrl):
    api_class = api_cash_ctrl.CustomField
    exclude = EXCLUDE_FIELDS + ['code', 'group_ref', 'notes', 'is_inactive']

    def get(self, setup, created_by, params={}, update=True):
        for field in api_cash_ctrl.FIELD_TYPE:
            params = {'type': field.value}
            super().get(setup, created_by, params, update)

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

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"


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
        if instance.setup.encode_numbers and not instance.is_top_level_account:
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
        if instance.setup.encode_numbers:
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

    def adjust_for_upload(self, instance, data, created=None):
        return  # currently only get

    def save_download(self, instance, data):
        instance.c_id = 1  # always
        instance.modified_at = timezone.now()

        # Add Accounts
        for key, value in data.items():
            if key.endswith('_account_id'):
                foreign_key = models.Account.objects.filter(
                    setup=self.setup, c_id=value).first()
                setattr(instance, key, foreign_key)

    def get(self, setup, created_by, params={}, update=True):
        api = self._get_api(setup)
        data = api.read()
        data['id'] = 1  # enforce settings to have an id
        data = {k.lower(): v for k, v in data.items()}  # convert cases

        if update:
            action = self.model.objects.update_or_create
        else:
            action = self.model.objects.get_or_create

        obj, created = action(
            setup=setup, c_id=data.pop('id'), defaults=dict(
                tenant=setup.tenant,
                created_by=created_by,
                **data
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

        # status, we only use minimal values as we do the booking ourselves
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
            'isAllowTax': True if instance.tax else False,
            'taxId': instance.tax.c_id if instance.tax else None
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


class Order(CashCtrl):
    api_class = api_cash_ctrl.Order
    exclude = EXCLUDE_FIELDS
    reload_keys = ['nr']
    abstract = True

    def make_base(self, instance, data):
        # Category, person
        data['category_id'] = instance.category.c_id
        if instance.responsible_person:
            person = models.Person.objects.filter(
                core=instance.responsible_person).first()
            data['responsible_person_id'] = person.c_id if person else None

        # status_id - temp!!! Later with dynamic form
        for index, status in enumerate(models.OrderCategoryIncoming.STATUS):
            if instance.status == status:
                break
        data['status_id'] = instance.category.status_data[index]['id']


class OrderContract(Order):

    def adjust_for_upload(self, instance, data, created=None):
        self.make_base(instance, data)

        # associate
        person = models.Person.objects.filter(
            core=instance.associate).first()
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
            person = models.Person.objects.filter(
                core=instance.associate).first()
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
            person = models.Person.objects.filter(
                core=instance.contract.associate).first()
            data['associate_id'] = person.c_id if person else None

        # Create one item with total price
        category = instance.category
        bank_account = PersonBankAccount.objects.filter(
            tenant=instance.tenant, 
            person=instance.contract.associate,
            type=PersonBankAccount.TYPE.DEFAULT
        ).first()
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
            
        print("*data", data)    
            

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
class Title(CashCtrlDual):
    api_class = api_cash_ctrl.PersonTitle
    exclude = EXCLUDE_FIELDS + ['code']
    model_accounting = models.Title

    def adjust_for_upload(self, instance, data, created=None):
        return model_to_dict(instance, exclude=self.exclude)


class PersonCategory(CashCtrlDual):
    api_class = api_cash_ctrl.PersonCategory
    exclude = EXCLUDE_FIELDS + ['code']
    model_accounting = models.PersonCategory

    def adjust_for_upload(self, instance, data, created=None):
        return model_to_dict(instance, exclude=self.exclude)

    def save_download(self, instance, data):
        if not instance.code:
            instance.code = f"custom {data['id']}"


class Person(CashCtrlDual):
    api_class = api_cash_ctrl.Person
    exclude = EXCLUDE_FIELDS + ['photo']  # for now
    reload_keys = ['nr']
    model_accounting = models.Person

    def adjust_for_upload(self, instance, data, created=None):
        # Make data

        # Category
        data['category_id'] = models.PersonCategory.objects.get(
            core=instance.category).c_id

        # superior
        superior = models.Person.objects.filter(
            core=instance.superior).first()
        if superior:
            data['superior_id'] = superior.c_id

        # Add Title
        title = models.Title.objects.filter(core=instance.title).first()
        if title:
            data['title_id'] = title.c_id

        # Make Bank accoutns
        bank_accounts = PersonBankAccount.objects.filter(person=instance)
        data['bank_accounts'] = [{
            'type': account.type,
            'iban': account.iban,
            'bic': account.bic
        } for account in bank_accounts.order_by('id')]

        # Make contacts
        contacts = PersonContact.objects.filter(person=instance)
        data['contacts'] = [{
            'type': contact.type,
            'address': contact.address
        } for contact in contacts.order_by('id')]

        # Make addresses
        addresses = PersonAddress.objects.filter(person=instance)
        data['addresses'] = [{
            'type': addr.type,
            'address': addr.address_full,
            'city': addr.address.city,
            'country': addr.address.country.alpha3,
            'zip': addr.address.zip
        } for addr in addresses.order_by('id')]

    def save(self, instance, created=None):
        '''
        Write back nr to Person if created
        '''
        super().save(instance, created)

        # get the full record to update status
        self.instance_acct.refresh_from_db()
        data = self.api.read(self.instance_acct.c_id)
        instance.nr = data['nr']

        # save
        instance.sync_to_accounting = False
        instance.save()
