# views.py
from django.shortcuts import render

def documentation(request):
    return render(request, 'docu/build/html/index.html')
