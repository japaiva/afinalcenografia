from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import boto3
from botocore.client import Config

class MinioStorage(S3Boto3Storage):
    """
    Storage personalizado para o MinIO, com configuração explícita do cliente S3
    """
    def __init__(self, *args, **kwargs):
        # Configurações necessárias antes de chamar super().__init__
        kwargs['bucket_name'] = settings.AWS_STORAGE_BUCKET_NAME
        kwargs['access_key'] = settings.AWS_ACCESS_KEY_ID
        kwargs['secret_key'] = settings.AWS_SECRET_ACCESS_KEY
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
        kwargs['file_overwrite'] = False
        kwargs['default_acl'] = settings.AWS_DEFAULT_ACL
        kwargs['querystring_auth'] = settings.AWS_QUERYSTRING_AUTH
        
        # Inicializar a classe pai
        super().__init__(*args, **kwargs)
        
        # Criar cliente S3 como um atributo normal (não property)
        self._connection = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
    
    def url(self, name, parameters=None, expire=None):
        """
        Gera URL para o objeto armazenado.
        """
        try:
            # Para arquivos públicos
            if not self.querystring_auth:
                # Construir a URL manualmente
                return f"{self.endpoint_url}/{self.bucket_name}/{name}"
            
            # Para arquivos privados (com assinatura)
            params = parameters.copy() if parameters else {}
            return self._connection.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': name, **params},
                ExpiresIn=expire or 3600
            )
        except Exception as e:
            print(f"Erro ao gerar URL: {e}")
            return super().url(name, parameters, expire)