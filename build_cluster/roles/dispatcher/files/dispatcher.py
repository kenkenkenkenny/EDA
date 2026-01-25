from celery import Celery

BROKER = "amqp://admin:abc123@10.134.12.238:5672//"
BACKEND = "rpc://"
TASK = "pipeline.run_by_id"
QUEUE = "pipeline"
IDS_FILE = "experiment_ids.txt"

app = Celery("dispatcher", broker=BROKER, backend=BACKEND)

def main():
    with open(IDS_FILE) as f:
        ids = [line.strip() for line in f if line.strip()]

    print("total ids:", len(ids))

    for i, pid in enumerate(ids, 1):
        app.send_task(TASK, args=[pid], queue=QUEUE)
        if i % 100 == 0:
            print("dispatched:", i)

    print("done. dispatched:", len(ids), "to queue:", QUEUE)

if __name__ == "__main__":
    main()