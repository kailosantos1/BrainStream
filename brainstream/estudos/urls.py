from django.urls import path

from . import views

app_name = 'estudos'

urlpatterns = [
    path('estudo/<int:sessao_id>/', views.modo_guiado, name='modo_guiado'),
    path('estudo/quiz/<int:sessao_id>/', views.modo_quiz, name='modo_quiz'),
    path('estudo/speedrun/<int:sessao_id>/', views.modo_speedrun, name='modo_speedrun'),
    path('estudo/<int:sessao_id>/excluir/', views.excluir_sessao, name='excluir_sessao'),
]
