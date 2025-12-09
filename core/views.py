from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test, login_required
from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Formulario para crear usuario de solo lectura
class UsuarioLecturaForm(forms.Form):
    username = forms.CharField(label='Usuario', max_length=150)
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)

# Solo admin puede acceder
@user_passes_test(lambda u: u.is_superuser)
def crear_usuario_lectura(request):
    mensaje = None
    if request.method == 'POST':
        form = UsuarioLecturaForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, email=email, password=password)
                user.is_staff = False
                user.save()
                mensaje = f"Usuario '{username}' creado correctamente."
                return redirect('/usuarios/editar/?mensaje=creado')
            else:
                mensaje = f"El usuario '{username}' ya existe."
    else:
        form = UsuarioLecturaForm()
    usuarios = User.objects.filter(is_staff=False, is_superuser=False)
    return render(request, 'usuarios/crear_usuario.html', {'form': form, 'mensaje': mensaje, 'usuarios': usuarios})

class EditarUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'is_active']

@user_passes_test(lambda u: u.is_superuser)
def editar_usuarios(request):
    usuarios = User.objects.filter(is_superuser=False)
    mensaje = request.GET.get('mensaje')
    eliminar_id = request.GET.get('eliminar')
    if eliminar_id:
        usuario_a_eliminar = User.objects.filter(id=eliminar_id, is_superuser=False).first()
        if usuario_a_eliminar:
            usuario_a_eliminar.delete()
            return redirect('/usuarios/editar/?mensaje=eliminado')
    if request.method == 'POST' and not request.GET.get('eliminar'):
        user_id = request.POST.get('user_id')
        usuario = get_object_or_404(User, id=user_id)
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('/usuarios/editar/?mensaje=editado')
    else:
        forms_dict = {u.id: EditarUsuarioForm(instance=u) for u in usuarios}
    return render(request, 'usuarios/editar_usuarios.html', {'usuarios': usuarios, 'forms_dict': forms_dict, 'mensaje': mensaje})

# Create your views here.

def index(request):
    """Vista principal: dashboard (requiere login)"""
    # Si el usuario no está autenticado, lo redirige automáticamente al login
    # El decorador login_required se encarga de esto
    pass  # El decorador se agregará abajo


@login_required(login_url='/login/')
def index(request):
    """Vista principal: dashboard (requiere login)"""
    return render(request, "dashboard.html")

@api_view(['GET'])
def api_status(request):
    """Estado de la API"""
    return Response({
        'status': 'ok',
        'message': 'PrestaLabs API está funcionando'
    })