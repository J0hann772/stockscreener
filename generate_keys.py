"""
Скрипт для генерации RSA ключей (RS256).

Создаёт пару private.pem / public.pem и раскладывает их
в три папки: keys/, django_service/keys/, fastapi_service/keys/.
Django получает оба ключа (для подписи и проверки),
FastAPI — только публичный (для проверки).
"""
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_keys():
    """
    Генерирует RSA ключи и раскладывает по сервисам.

    Создаёт приватный ключ (2048 бит) и извлекает из него публичный.
    Сохраняет ключи в формате PEM в три директории:
        - keys/ — корневая папка (бекап)
        - django_service/keys/ — приватный + публичный
        - fastapi_service/keys/ — только публичный
    """
    # Если задана переменная окружения JWT_KEYS_DIR, генерируем только в нее
    jwt_keys_dir = os.environ.get('JWT_KEYS_DIR')
    if jwt_keys_dir:
        os.makedirs(jwt_keys_dir, exist_ok=True)
        priv_path = os.path.join(jwt_keys_dir, 'private.pem')
        pub_path = os.path.join(jwt_keys_dir, 'public.pem')
        if os.path.exists(priv_path) and os.path.exists(pub_path):
            print(f"Keys already exist in {jwt_keys_dir}. Skipping.")
            return
        
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pem_public = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(priv_path, 'wb') as f: f.write(pem_private)
        with open(pub_path, 'wb') as f: f.write(pem_public)
        print(f"Keys generated successfully in {jwt_keys_dir}")
        return

    # Создаем папки если их нет (для локальной разработки)
    keys_dir = 'keys'
    django_keys_dir = os.path.join('django_service', 'keys')
    fastapi_keys_dir = os.path.join('fastapi_service', 'keys')
    
    for d in [keys_dir, django_keys_dir, fastapi_keys_dir]:
        os.makedirs(d, exist_ok=True)

    # Проверяем, существуют ли уже ключи
    if os.path.exists(os.path.join(django_keys_dir, 'private.pem')) and os.path.exists(os.path.join(fastapi_keys_dir, 'public.pem')):
        print("Keys already exist. Skipping generation.")
        return

    # Генерируем приватный ключ
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Получаем публичный ключ
    public_key = private_key.public_key()

    # Сериализуем и сохраняем приватный ключ
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Сериализуем и сохраняем публичный ключ
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # В основную папку (для истории/бекапа при локальной разработке)
    with open(os.path.join(keys_dir, 'private.pem'), 'wb') as f:
        f.write(pem_private)
    with open(os.path.join(keys_dir, 'public.pem'), 'wb') as f:
        f.write(pem_public)

    # В Django (ему нужен и приватный для подписи, и публичный для проверки)
    with open(os.path.join(django_keys_dir, 'private.pem'), 'wb') as f:
        f.write(pem_private)
    with open(os.path.join(django_keys_dir, 'public.pem'), 'wb') as f:
        f.write(pem_public)

    # В FastAPI (ему нужен только публичный для проверки подписи)
    with open(os.path.join(fastapi_keys_dir, 'public.pem'), 'wb') as f:
        f.write(pem_public)
        
    print("Keys generated and distributed successfully!")


if __name__ == "__main__":
    generate_keys()
