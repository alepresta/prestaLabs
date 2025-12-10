from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib import messages
from .forms import UsuarioLecturaForm, EditarUsuarioForm


def analisis_dominio(request):
    """
    Vista placeholder para análisis de dominio
    """
    return render(request, "analisis_dominio.html")


@method_decorator(user_passes_test(lambda u: u.is_superuser), name="dispatch")
class ListarUsuariosView(View):
    """
    CBV para listar todos los usuarios (solo admin)
    """

    def get(self, request):
        usuarios = User.objects.filter(is_superuser=False)
        q = request.GET.get("q", "").strip().lower()
        tipo = request.GET.get("tipo", "")
        if q:
            usuarios = usuarios.filter(username__icontains=q) | usuarios.filter(
                email__icontains=q
            )
        if tipo == "admin":
            usuarios = usuarios.filter(is_staff=True)
        elif tipo == "lectura":
            usuarios = usuarios.filter(is_staff=False)
        return render(
            request,
            "usuarios/listar_usuarios.html",
            {"usuarios": usuarios},
        )


def dashboard_redirect(request):
    """
    Redirige /dashboard a login si no está autenticado, o al index si sí
    """
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    return redirect("index")


# Formulario para crear usuario de solo lectura


# Solo admin puede acceder


@method_decorator(user_passes_test(lambda u: u.is_superuser), name="dispatch")
class CrearUsuarioLecturaView(View):
    """
    CBV para crear usuario de solo lectura (solo admin)
    """

    def get(self, request):
        form = UsuarioLecturaForm()
        usuarios = User.objects.filter(is_staff=False, is_superuser=False)
        return render(
            request,
            "usuarios/crear_usuario.html",
            {"form": form, "usuarios": usuarios},
        )

    def post(self, request):
        form = UsuarioLecturaForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )
                user.is_staff = False
                user.save()
                messages.success(
                    request,
                    ("Usuario '" + str(username) + "' creado correctamente."),
                )
                return redirect("/usuarios/editar/")
            else:
                messages.error(request, f"El usuario '{username}' ya existe.")
        usuarios = User.objects.filter(is_staff=False, is_superuser=False)
        return render(
            request,
            "usuarios/crear_usuario.html",
            {"form": form, "usuarios": usuarios},
        )


@method_decorator(user_passes_test(lambda u: u.is_superuser), name="dispatch")
class EditarUsuariosView(View):
    """
    CBV para editar usuarios (solo admin)
    """

    def get(self, request):
        usuarios = User.objects.filter(is_superuser=False)
        forms_dict = {u.id: EditarUsuarioForm(instance=u) for u in usuarios}
        return render(
            request,
            "usuarios/editar_usuarios.html",
            {"usuarios": usuarios, "forms_dict": forms_dict},
        )

    def post(self, request):
        usuarios = User.objects.filter(is_superuser=False)
        eliminar_id = request.POST.get("eliminar_id")
        if eliminar_id:
            usuario_a_eliminar = User.objects.filter(
                id=eliminar_id, is_superuser=False
            ).first()
            if usuario_a_eliminar:
                usuario_a_eliminar.delete()
                messages.success(request, "Usuario eliminado correctamente.")
                return redirect("/usuarios/editar/")
        user_id = request.POST.get("user_id")
        if user_id:
            usuario = get_object_or_404(User, id=user_id)
            form = EditarUsuarioForm(request.POST, instance=usuario)
            if form.is_valid():
                form.save()
                messages.success(request, "Usuario editado correctamente.")
                return redirect("/usuarios/editar/")
        forms_dict = {u.id: EditarUsuarioForm(instance=u) for u in usuarios}
        return render(
            request,
            "usuarios/editar_usuarios.html",
            {"usuarios": usuarios, "forms_dict": forms_dict},
        )


@method_decorator(user_passes_test(lambda u: u.is_superuser), name="dispatch")
class ExportarUsuariosView(View):
    """
    Exporta los usuarios en formato CSV (solo admin)
    """

    def post(self, request):
        import csv
        from django.http import HttpResponse

        usuarios = User.objects.filter(is_superuser=False)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="usuarios.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["Usuario", "Email", "Tipo", "Fecha de Creación", "Último Acceso"]
        )
        for u in usuarios:
            tipo = "Admin" if u.is_staff else "Lectura"
            writer.writerow(
                [
                    u.username,
                    u.email,
                    tipo,
                    u.date_joined.strftime("%d/%m/%Y %H:%M"),
                    u.last_login.strftime("%d/%m/%Y %H:%M") if u.last_login else "-",
                ]
            )
        return response


def index(request):
    """
    Vista principal: dashboard (requiere login)
    """
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    return render(request, "dashboard.html")


@api_view(["GET"])
def api_status(request):
    """
    Estado de la API
    """
    return Response(
        {
            "status": "ok",
            "message": "PrestaLabs API está funcionando",
        }
    )
