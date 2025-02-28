from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from scerp.admin import BaseAdminNew
from scerp.admin_base import TenantFilteringAdmin, FIELDS as FIELDS_BASE


class FIELDS:
    SUPER_USER_EDITABLE_FIELDS = (
        'message',
        'is_enabled_sync',
        'sync_to_accounting',
        'setup'
    )
    C_FIELDS = (
        'c_id',
        'c_created',
        'c_created_by',
        'c_last_updated',
        'c_last_updated_by',
        'last_received',
    )    
    C_DISPLAY = (
        'display_last_update', 'c_id', 'message', 'is_enabled_sync')
    C_DISPLAY_SHORT = ('c_id', 'is_enabled_sync')
    C_ALL = C_FIELDS + C_DISPLAY
    C_READ_ONLY = FIELDS_BASE.LOGGING_SETUP + C_FIELDS + ('setup',)


class FIELDSET:
    CASH_CTRL = (
        'cashCtrl', {
            'fields': FIELDS.C_FIELDS + FIELDS.SUPER_USER_EDITABLE_FIELDS,
            'classes': ('collapse',),
        })    
    

class CashCtrlAdmin(BaseAdminNew):
    '''
    main class: TenantFilteringAdmin + same displays
    '''
        
    @admin.display(description=_('last update'))
    def display_last_update(self, obj):
        return obj.modified_at

    @admin.display(description=_('Name Plural'))
    def display_name_plural(self, obj):
        try:
            return primary_language(obj.name_plural)
        except:
            return ''

    @admin.display(description=_('Parent'))
    def display_parent(self, obj):
        return self.display_name(obj.parent)

    @admin.display(description=_('Balance'))
    def display_link_to_company(self, person):
        if not person.company:
            return "-"  # Fallback if company is missing
        url = f"../person/{person.id}/"
        return format_html('<a href="{}">{}</a>', url, person.company)

    @admin.display(
        description=_('function'))
    def display_function(self, obj):
        return obj.account_number if obj.is_category else ' '

    @admin.display(description=_('position nr.'))
    def position_number(self, obj):
        return ' ' if obj.is_category else obj.account_number

    @admin.display(description=_('actual +'))
    def display_end_amount_credit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.EXPENSE, CATEGORY_HRM.ASSET):
            balance = 0 if obj.end_amount is None else obj.end_amount
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('actual -'))
    def display_end_amount_debit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.REVENUE, CATEGORY_HRM.LIABILITY):
            balance = 0 if obj.end_amount is None else obj.end_amount
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('balance +'))
    def display_balance_credit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.EXPENSE, CATEGORY_HRM.ASSET):
            balance = 0 if obj.balance is None else obj.balance
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('balance -'))
    def display_balance_debit(self, obj):
        if obj.category_hrm in (CATEGORY_HRM.REVENUE, CATEGORY_HRM.LIABILITY):
            balance = 0 if obj.balance is None else obj.balance
            return Display.big_number(balance)
        return ' '

    @admin.display(description=_('balance'))
    def display_balance(self, obj):
        balance = 0 if obj.balance is None else obj.balance
        return Display.big_number(balance)

    @admin.display(description=_('budget'))
    def display_budget(self, obj):
        return Display.big_number(obj.budget)

    @admin.display(description=_('previous'))
    def display_previous(self, obj):
        return Display.big_number(obj.previous)

    @admin.display(description=_(''))
    def display_cashctrl(self, obj):
        if obj.c_id or obj.c_rev_id:
            return '🪙'  # (Coin): \U0001FA99
        return ' '
