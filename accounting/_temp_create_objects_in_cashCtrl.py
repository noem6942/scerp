   # FiscalPeriod
    def create_fiscal_period(self, obj):            
        # Create, we do is_custom=True, we don't assign type
        data = {
            'name': obj.name,
            'is_custom': True,
            'start': obj.start,
            'end': obj.end
        }        
        fp = self.ctrl.create(API.fiscalperiod.value['url'], data)
        if fp.get('success'):         
            # Get data
            fiscal_periods = self.ctrl.list(API.fiscalperiod.value['url'])
            period = next(
                (x for x in fiscal_periods if x['name'] == obj.name), None)
                
            # Save    
            if period:       
                self.save_application_logging(obj, period)
                obj.save()            
            else:
                raise Exception(f"Period '{obj.name}' not found.")

    def update_fiscal_period(self, obj):
        data = {
            'id': obj.c_id,
            'name': obj.name,
            'is_custom': True,
            'start': obj.start,
            'end': obj.end
        }
        fp = self.ctrl.update(API.fiscalperiod.value['url'], data)

    # Location
    def update_read_records(self, api_class, model):
        # Get data

        data_list = self.ctrl.list(api_class.value['url'])
 
        # Init
        count = 0
        instance = model()
        model_keys = instance.__dict__.keys()  

        # Parse
        for data in data_list:
            # Clean basics
            data.update({
                'c_id': data.pop('id'),
                'c_created': self.make_timeaware(data.pop('created')),
                'c_created_by': data.pop('created_by'),
                'c_last_updated': self.make_timeaware(
                    data.pop('last_updated')),
                'c_last_updated_by': data.pop('last_updated_by')
            })                       
            
            # Remove keys not needed
            for key in list(data.keys()):
                if key  not in model_keys:
                    data.pop(key)  

            # Add logging info
            self.add_logging(data)
            
            # Update or create
            _obj, created = model.objects.update_or_create(
                tenant=self.api_setup.tenant,
                setup=data.pop('setup'),
                c_id=data.pop('c_id'),
                defaults=data)
            if created:
                count += 1
        
        return count