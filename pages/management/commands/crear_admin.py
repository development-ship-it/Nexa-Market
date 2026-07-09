from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Crea el usuario administrador admin/1234'

    def handle(self, *args, **options):
        if User.objects.filter(username='admin').exists():
            self.stdout.write(self.style.WARNING('El usuario admin ya existe.'))
            return
        User.objects.create_superuser(
            username='admin',
            email='admin@nexamarket.com',
            password='1234',
        )
        self.stdout.write(self.style.SUCCESS('Usuario admin creado: admin / 1234'))
