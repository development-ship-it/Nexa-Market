import django.db.models.deletion
from django.db import migrations, models


def seed_plans(apps, schema_editor):
    Plan = apps.get_model('base_datos', 'Plan')
    Plan.objects.bulk_create([
        Plan(
            nombre='Gratuito',
            descripcion='Acceso completo de forma local. Sin sincronización en la nube.',
            precio_base=0,
            precio_por_usuario=0,
        ),
        Plan(
            nombre='Pro',
            descripcion='Sincronización en la nube. $15.000 CLP + IVA base + $5.000 CLP + IVA por usuario activo.',
            precio_base=15000,
            precio_por_usuario=5000,
        ),
    ])


def set_default_plan(apps, schema_editor):
    Plan = apps.get_model('base_datos', 'Plan')
    Empresa = apps.get_model('base_datos', 'Empresa')
    try:
        gratuito = Plan.objects.get(nombre='Gratuito')
        Empresa.objects.filter(id_plan__isnull=True).update(id_plan=gratuito)
    except Plan.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('base_datos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id_plan', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('precio_base', models.IntegerField(default=0)),
                ('precio_por_usuario', models.IntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
            ],
            options={
                'verbose_name': 'Plan',
                'verbose_name_plural': 'Planes',
                'db_table': 'plan',
            },
        ),
        migrations.RunPython(seed_plans, reverse_code=migrations.RunPython.noop),
        migrations.AddField(
            model_name='empresa',
            name='id_plan',
            field=models.ForeignKey(
                blank=True,
                db_column='id_plan',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='empresas',
                to='base_datos.plan',
            ),
        ),
        migrations.RunPython(set_default_plan, reverse_code=migrations.RunPython.noop),
        migrations.AddField(
            model_name='empresa',
            name='usuarios_activos',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='usuario',
            name='device_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='es_super_admin',
            field=models.BooleanField(default=False),
        ),
    ]
