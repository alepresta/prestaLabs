from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Create your views here.

def index(request):
    """Vista principal"""
    return HttpResponse("<h1>Bienvenido a PrestaLabs</h1>")

@api_view(['GET'])
def api_status(request):
    """Estado de la API"""
    return Response({
        'status': 'ok',
        'message': 'PrestaLabs API está funcionando'
    })