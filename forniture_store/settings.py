import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))

# Carrega variáveis do arquivo .env se ele existir
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# --- Configurações de Segurança e Debug ---
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
# Converte o valor de DJANGO_DEBUG para booleano, padrão 'False' se não definido
DEBUG_STRING = os.environ.get("DJANGO_DEBUG", "False")
DEBUG = DEBUG_STRING.lower() in ("true", "1", "t")


if not SECRET_KEY:
    if DEBUG:
        print(
            "AVISO DE DESENVOLVIMENTO: DJANGO_SECRET_KEY não definida, usando uma chave de fallback. Defina no .env!"
        )
        SECRET_KEY = (
            "django-insecure-p9y-*a(1fi9o#l5g2_h1k(j6=lb8jb-t%-k^u4-tdup)tl+&n7"  # Chave de fallback apenas para DEBUG
        )
    else:
        raise ValueError(
            "ERRO CRÍTICO: DJANGO_SECRET_KEY não está definida para o ambiente de produção!"
        )

if DEBUG:
    ALLOWED_HOSTS = ["*"]  # Em debug, permite todos os hosts
else:
    allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS")
    if allowed_hosts_env:
        ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",")]
    else:
        ALLOWED_HOSTS = []
        print(
            "AVISO CRÍTICO DE PRODUÇÃO: DJANGO_ALLOWED_HOSTS não está definida. A aplicação pode não responder a requisições ou estar insegura."
        )


# --- Configuração do Banco de Dados ---
DB_ENGINE_ENV = os.environ.get('DB_ENGINE', 'django.db.backends.postgresql')
DB_NAME_ENV = os.environ.get('DB_NAME')
DB_USER_ENV = os.environ.get('DB_USER')
DB_PASSWORD_ENV = os.environ.get('DB_PASSWORD')
DB_HOST_ENV = os.environ.get('DB_HOST', 'localhost')
DB_PORT_ENV = os.environ.get('DB_PORT', '5432')

if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=os.environ.get('DB_SSL_REQUIRE', 'False').lower() == 'true')
    }
else:
    # Configuração de fallback para desenvolvimento local (se DATABASE_URL não estiver definida)
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE_ENV,
            'NAME': DB_NAME_ENV,
            'USER': DB_USER_ENV,
            'PASSWORD': DB_PASSWORD_ENV,
            'HOST': DB_HOST_ENV,
            'PORT': DB_PORT_ENV,
        }
    }

if not DEBUG:
    db_configured = False
    if 'DATABASE_URL' in os.environ and os.environ['DATABASE_URL']:
        db_configured = True
    elif all([DB_NAME_ENV, DB_USER_ENV, DB_PASSWORD_ENV]): # Fallback para local se DEBUG=False e sem DATABASE_URL
        db_configured = True

    if not db_configured:
        raise ValueError(
            "ERRO CRÍTICO DE PRODUÇÃO: Configuração do banco de dados (DATABASE_URL ou DB_NAME/USER/PASSWORD) não está definida!"
        )
    
# Verificação para garantir que as variáveis de ambiente do banco de dados estão definidas
# Esta verificação é importante para qualquer ambiente, mas crítica para produção
if not all([DB_NAME_ENV, DB_USER_ENV, DB_PASSWORD_ENV]): # ENGINE, HOST, PORT têm defaults
    # Se DEBUG for True, apenas um aviso. Se False (produção), um erro.
    message = "As variáveis de ambiente DB_NAME, DB_USER ou DB_PASSWORD não estão definidas!"
    if DEBUG:
        print(f"AVISO DE DESENVOLVIMENTO: {message} Verifique seu arquivo .env.")
    else:
        raise ValueError(f"ERRO CRÍTICO DE PRODUÇÃO: {message}")


# --- Configurações de Aplicação ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    ## My Apps
    "apps.addresses",
    "apps.customers",
    "apps.docs",
    "apps.employees",
    "apps.showroom",
    # 'apps.reports',
    # 'apps.orders',
    # 'apps.products',
    # 'apps.stock',
    # 'apps.suppliers',
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "forniture_store.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates")
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.employees.context_processors.theme_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "forniture_store.wsgi.application"


# --- Configurações de Validação de Senha ---
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# --- Configurações de Internacionalização ---
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# --- Configurações de Arquivos Estáticos e Mídia ---
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # Para 'collectstatic' em produção
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # Para compressão e cache busting
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"), # Para desenvolvimento
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# --- Modelo de Usuário Personalizado e URLs de Autenticação ---
AUTH_USER_MODEL = "employees.Employee"
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"


# --- Configurações de Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO", # Nível de log depende do DEBUG
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": { # Logger raiz do Django
            "handlers": ["console"],
            "level": "INFO", # Evita spam do Django em modo DEBUG
            "propagate": False,
        },
        "apps": { # Logger para suas apps, se você usar logging.getLogger('apps.algumacoisa')
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": True,
        },
    },
    "root": { # Logger raiz para capturar logs não tratados
        "handlers": ["console"],
        "level": "INFO",
    },
}

# --- Configuração de E-mail ---
# Para desenvolvimento, e-mails são impressos no console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# # Em produção, configure um backend SMTP real
# if not DEBUG:
#     EMAIL_BACKEND_PROD = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
#     EMAIL_HOST_PROD = os.environ.get('DJANGO_EMAIL_HOST')
#     EMAIL_PORT_PROD = os.environ.get('DJANGO_EMAIL_PORT', 587) # Padrão para TLS
#     EMAIL_USE_TLS_PROD = os.environ.get('DJANGO_EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
#     EMAIL_HOST_USER_PROD = os.environ.get('DJANGO_EMAIL_HOST_USER')
#     EMAIL_HOST_PASSWORD_PROD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD')
#     DEFAULT_FROM_EMAIL_PROD = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', EMAIL_HOST_USER_PROD)

#     if EMAIL_BACKEND_PROD == 'django.core.mail.backends.smtp.EmailBackend':
#         if not all([EMAIL_HOST_PROD, EMAIL_HOST_USER_PROD, EMAIL_HOST_PASSWORD_PROD]):
#             print(
#                 "AVISO CRÍTICO DE PRODUÇÃO: Configurações de e-mail SMTP (HOST, USER, PASSWORD) não estão completas no .env!"
#             )
#             # Você pode optar por não configurar EMAIL_BACKEND se as variáveis não estiverem prontas
#             # ou manter console.EmailBackend como fallback se preferir não enviar e-mails.
#         else:
#             EMAIL_BACKEND = EMAIL_BACKEND_PROD
#             EMAIL_HOST = EMAIL_HOST_PROD
#             EMAIL_PORT = int(EMAIL_PORT_PROD)
#             EMAIL_USE_TLS = EMAIL_USE_TLS_PROD
#             EMAIL_HOST_USER = EMAIL_HOST_USER_PROD
#             EMAIL_HOST_PASSWORD = EMAIL_HOST_PASSWORD_PROD
#             DEFAULT_FROM_EMAIL = DEFAULT_FROM_EMAIL_PROD
