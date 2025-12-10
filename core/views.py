from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.contrib import messages
from .forms import EditarUsuarioForm
from rest_framework.decorators import api_view
from rest_framework.response import Response


def dashboard_redirect(request):
    """
    Redirige /dashboard a login si no está autenticado, o al index si sí
    """
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    return redirect("index")


class AnalisisUrlView(View):
    template_name = "analisis_url.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        url = request.POST.get("url")
        # Aquí iría la lógica real de análisis de la URL
        resultado = f"Análisis realizado para la URL: {url}\n[Simulación de resultado]"
        return render(
            request,
            self.template_name,
            {"resultado": resultado},
        )


class AnalisisDominioView(View):
    template_name = "analisis_dominio.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        dominio = request.POST.get("dominio")
        max_paginas = request.POST.get("max_paginas")
        concurrencia = request.POST.get("concurrencia")
        # Aquí iría la lógica real de análisis y generación de sitemap
        resultado = (
            f"Sitemap generado para {dominio} "
            f"(máx. páginas: {max_paginas}, concurrencia: {concurrencia})\n[Simulación de resultado]"
        )
        return render(
            request,
            self.template_name,
            {"resultado": resultado},
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
