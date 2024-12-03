# import_accounts_gesoft.py
from enum import Enum
from openpyxl import load_workbook


class ACCOUNT_TYPE:
    # Used for Cantonal Charts
    BALANCE = 1
    FUNCTIONAL = 2
    INCOME = 3
    INVEST = 5


class ACCOUNT_SIDE:
    # Used for assignment
    EXPENSE = 1
    INCOME = 2 
    CLOSING = 9


class ACCOUNT_CATEGORY_TYPE(Enum):
    # Used for cashctrl
    ASSET = 1  # Aktiven 
    LIABILITY = 2  # Passiven
    EXPENSE = 3  # Aufwand (INCOME), Ausgaben (INVEST),
    REVENUE = 4  # Ertrag (INCOME), Einnahmen (INVEST),
    BALANCE = 5  # 


class Import(object):

    def __init__(self, file_path, account_type, account_side=None):
        # Account
        self.account_type = account_type
        self.account_side = account_side
        
        # read content
        workbook = load_workbook(file_path)

        # Get a specific sheet
        sheet = workbook.active  # Default to the first sheet or use workbook['SheetName']
        
        # Iterate over rows and columns
        # `values_only=True` gets only cell values
        self.rows = [row for row in sheet.iter_rows(values_only=True)] 

    @staticmethod
    def clean_number(value):
        return value
    
    @staticmethod
    def get_value(*values):
        return next((x for x in values if x is not None), None)

    def get_accounts(self):
        accounts = []
        row_count = len(self.rows)
        for nr, row in enumerate(self.rows):       
            cells = list(row)  # convert tuple to list
            if type(cells[0]) in [int, float]:
                # Init
                account_number = cells.pop(0)            
                name = cells.pop(0)                              
                is_category = (type(account_number) == int)  # no '.' in value

                # check if broken name in next row
                if nr < row_count - 1:
                    next_row = self.rows[nr + 1]
                    if next_row[0] is None and next_row[1]:
                        name += ' ' + next_row[1]

                # Check closing
                if self.account_side == ACCOUNT_SIDE.CLOSING:
                    if str(account_number)[:2] != '99':
                        continue
                
                # Process
                if self.account_type == ACCOUNT_TYPE.BALANCE:
                    # Init
                    function = None
                    budget = None
                    
                    # Read balance                                        
                    balance, _in, _out, previous = cells                    
                    
                elif self.account_type == ACCOUNT_TYPE.INCOME:
                    # read income                    
                    (income, expense,
                     budget_income, budget_expense,
                     previous_income, previous_expense
                    ) = cells 

                    # Get function                    
                    if is_category:
                        function = account_number      
                        if (self.account_side == ACCOUNT_SIDE.EXPENSE
                                  or self.account_side == ACCOUNT_SIDE.CLOSING):
                            balance = expense
                            budget = budget_expense
                            previous = previous_expense
                        elif self.account_side == ACCOUNT_SIDE.INCOME:
                            balance = income
                            budget = budget_income
                            previous = previous_income                      
                    else:
                        if (self.account_side == ACCOUNT_SIDE.EXPENSE 
                                and 3000 <= account_number < 4000):
                            balance = expense
                            budget = budget_expense
                            previous = previous_expense
                        elif (self.account_side == ACCOUNT_SIDE.CLOSING 
                                and 9000 <= account_number == 9000.01):
                            balance = expense
                            budget = budget_expense
                            previous = previous_expense
                        elif (self.account_side == ACCOUNT_SIDE.INCOME 
                                  and 4000 <= account_number < 5000):
                            balance = income
                            budget = budget_income
                            previous = previous_income  
                        elif (self.account_side == ACCOUNT_SIDE.CLOSING 
                                and 9000 <= account_number == 9001.01):
                            balance = income
                            budget = budget_income
                            previous = previous_income  
                        else:
                            continue

                elif self.account_type == ACCOUNT_TYPE.INVEST:
                    # read invest
                    (expense, income, 
                     budget_expense, budget_income, 
                     previous_expense, previous_income,
                    ) = cells 

                    # Get function                    
                    if is_category:
                        function = account_number 
                        if self.account_side == ACCOUNT_SIDE.EXPENSE:
                            balance = expense
                            budget = budget_expense
                            previous = previous_expense
                        elif self.account_side == ACCOUNT_SIDE.INCOME:
                            balance = income
                            budget = budget_income
                            previous = previous_income                      
                    else:
                        if (self.account_side == ACCOUNT_SIDE.EXPENSE 
                                and 5000 <= account_number < 6000):
                            balance = expense
                            budget = budget_expense
                            previous = previous_expense
                        elif (self.account_side == ACCOUNT_SIDE.INCOME 
                                  and 6000 <= account_number < 7000):
                            balance = income
                            budget = budget_income
                            previous = previous_income    
                        else:
                            continue
                
                # Make account

                accounts.append({
                    'function': function,
                    'account_type': self.account_type,
                    'is_category': is_category,
                    'account_number': account_number,
                    'name': name,
                    'balance': self.clean_number(balance),
                    'budget': self.clean_number(budget),
                    'previous': self.clean_number(previous),
                })   
            
        return accounts
        
        
# main        
if __name__ == "__main__":
    # Bilanz    
    file_path = './fixtures/transfer ge_soft/Bilanz 2023 AGEM.xlsx'
    i = Import(file_path, ACCOUNT_TYPE.BALANCE)
    accounts = i.get_accounts()
    print("*** Bilanz", accounts[:10])

    # Income
    file_path = './fixtures/transfer ge_soft/Erfolgsrechnung 2023 AGEM.xlsx'

    i = Import(file_path,  ACCOUNT_TYPE.INCOME, ACCOUNT_SIDE.INCOME)
    accounts = i.get_accounts()
    print("*** Income / INCOME", accounts[:10])

    i = Import(file_path,  ACCOUNT_TYPE.INCOME, ACCOUNT_SIDE.EXPENSE)
    accounts = i.get_accounts()
    print("*** Income / EXPENSE", accounts[:10])

    i = Import(file_path,  ACCOUNT_TYPE.INCOME, ACCOUNT_SIDE.CLOSING)
    accounts = i.get_accounts()
    print("*** Income / CLOSING", accounts[:10])

    # Invest
    file_path = './fixtures/transfer ge_soft/IR-F JR Detail  (Q) SO_BE HRM2 DLIHB.SO.IR15.xlsx'
    i = Import(file_path, ACCOUNT_TYPE.INVEST, ACCOUNT_SIDE.INCOME)
    accounts = i.get_accounts()
    print("*** Invest / INCOME", accounts[:10])

    i = Import(file_path, ACCOUNT_TYPE.INVEST, ACCOUNT_SIDE.EXPENSE)
    accounts = i.get_accounts()
    print("*** Invest / EXPENSE", accounts[:10])
