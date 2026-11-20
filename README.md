# Лабораторная работа 8–9. HDFS и MinIO

[Отчёт со скриншотами и результатами](Lab_Report_Storage.pdf)

Стенд запускает один NameNode, два DataNode и один сервер MinIO. Нужны Docker с Compose и Python 3.10 или новее. Контейнер MinIO рассчитан на Linux amd64. Образ собирается из официального релиза MinIO с проверкой SHA-256, чтобы версия веб-консоли воспроизводилась при повторном запуске.

## Запуск

```powershell
docker compose up -d --build
docker compose ps
python -m pip install -r requirements.txt
```

HDFS Web UI доступен на http://localhost:9870, API S3 на http://localhost:9001, консоль MinIO на http://localhost:9002. Учебные данные для входа в локальную консоль заданы в Compose.

## Файл и репликация

Когда HDFS показывает два активных узла, создайте случайный файл размером 100 МиБ и используйте одни и те же байты в обоих хранилищах.

```powershell
docker exec hdfs_namenode hdfs dfs -mkdir -p /user/student/data
docker exec hdfs_namenode dd if=/dev/urandom of=/tmp/sample_100m.bin bs=1M count=100
docker exec hdfs_namenode hdfs dfs -put -f /tmp/sample_100m.bin /user/student/data/
docker exec hdfs_namenode hdfs fsck /user/student/data/sample_100m.bin -files -blocks -locations
docker cp hdfs_namenode:/tmp/sample_100m.bin sample_100m.bin
python -c "from s3_client import init_storage, upload_object; init_storage(); upload_object('sample_100m.bin', 'sample_100m.bin', {'course': 'CSS4004', 'storage': 'minio'})"
python -m pytest -q
```

Остановите один DataNode и дождитесь, пока NameNode отметит его как недоступный. Затем запустите его снова и проверьте, что число активных узлов вернулось к двум.

```powershell
docker stop hdfs_datanode1
# В веб-интерфейсе HDFS проверьте Dead Nodes и Under-Replicated Blocks.
docker start hdfs_datanode1
```

## Сравнение задержки

После восстановления HDFS запустите измерения из корня репозитория. Один контейнер-клиент читает полный файл через WebHDFS и S3, сверяет SHA-256 и выводит пять замеров для каждого хранилища в миллисекундах.

```powershell
docker run --rm --network lab-8-9_default -e LAB_S3_ENDPOINT=http://minio:9000 -v "${PWD}:/lab:ro" -w /lab python:3.12-slim sh -c "pip -q install --disable-pip-version-check --root-user-action=ignore -r requirements.txt && python benchmark_reads.py"
```
