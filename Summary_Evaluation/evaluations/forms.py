from cProfile import label
from django  import forms

class upload(forms.Form):
    file = forms.FileField(label = "Upload Data File (json only)")