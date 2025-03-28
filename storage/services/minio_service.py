from django.conf import settings
from minio import Minio
from minio.error import S3Error
import io
import os
import hashlib

class MinioService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        
        # Garantir que o bucket existe
        if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
            self.client.make_bucket(settings.MINIO_BUCKET_NAME)
    
    def upload_file(self, file_obj, object_name=None, content_type=None):
        """
        Faz upload de um arquivo para o Minio
        
        :param file_obj: Objeto de arquivo (InMemoryUploadedFile ou BytesIO)
        :param object_name: Nome do objeto no bucket (se None, usa o nome do arquivo)
        :param content_type: Tipo de conteúdo do arquivo
        :return: URL do objeto
        """
        if object_name is None:
            object_name = file_obj.name
            
        # Determinar o content_type caso não tenha sido fornecido
        if content_type is None:
            import mimetypes
            content_type, _ = mimetypes.guess_type(object_name)
            if content_type is None:
                content_type = 'application/octet-stream'
            
        try:
            # Calcular MD5 hash para verificação de integridade
            md5_hash = None
            if hasattr(file_obj, 'read'):
                file_data = file_obj.read()
                file_size = len(file_data)
                
                # Calcular MD5
                md5_hash = hashlib.md5(file_data).hexdigest()
                
                # Fazer upload do arquivo
                self.client.put_object(
                    bucket_name=settings.MINIO_BUCKET_NAME,
                    object_name=object_name,
                    data=io.BytesIO(file_data),
                    length=file_size,
                    content_type=content_type
                )
            else:
                # Para outros tipos de objetos
                self.client.fput_object(
                    bucket_name=settings.MINIO_BUCKET_NAME,
                    object_name=object_name,
                    file_path=file_obj,
                    content_type=content_type
                )
            
            # Registrar o arquivo no banco de dados
            from storage.models import ArquivoRastreamento
            rastreamento = ArquivoRastreamento.objects.create(
                nome_original=os.path.basename(object_name),
                path_minio=object_name,
                bucket=settings.MINIO_BUCKET_NAME,
                tipo_arquivo=content_type,
                tamanho=file_size if 'file_size' in locals() else 0,
                md5_hash=md5_hash
            )
            
            # Retornar a URL do objeto
            return self.get_file_url(object_name), rastreamento.id
                
        except S3Error as err:
            print(f"Erro ao fazer upload do arquivo: {err}")
            raise
    
    def get_file_url(self, object_name, expires=7*24*60*60):
        """
        Gera uma URL pré-assinada para o objeto
        
        :param object_name: Nome do objeto no bucket
        :param expires: Tempo de expiração em segundos (padrão: 7 dias)
        :return: URL pré-assinada
        """
        try:
            return self.client.presigned_get_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                expires=expires
            )
        except S3Error as err:
            print(f"Erro ao gerar URL do arquivo: {err}")
            raise
    
    def delete_file(self, object_name):
        """
        Remove um arquivo do bucket
        
        :param object_name: Nome do objeto a ser removido
        :return: True se sucesso, False se falha
        """
        try:
            # Tenta remover o arquivo do Minio
            self.client.remove_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name
            )
            
            # Tenta remover o registro do banco de dados
            from storage.models import ArquivoRastreamento
            ArquivoRastreamento.objects.filter(
                bucket=settings.MINIO_BUCKET_NAME,
                path_minio=object_name
            ).delete()
            
            return True
        except S3Error as err:
            print(f"Erro ao remover arquivo: {err}")
            return False