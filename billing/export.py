'''
billing/export.py
'''
from scerp.admin import Excel


class MeasurementExport:

    def __init__(self, modeladmin, request, queryset):
        self. modeladmin = modeladmin
        self.request = request
        self.queryset = queryset
        
    def get_excel(self):
        e = Excel()
        data = [
            (x.id, x.consumption)
            for x in self.queryset.all()
        ]
        response = e.generate_response(data)
        return response       
