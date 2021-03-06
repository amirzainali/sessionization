import sys
from pykafka import KafkaClient
from pykafka.partitioners import HashingPartitioner
from pykafka.partitioners import BasePartitioner
import numpy as np
import time
import json
sys.path.append("../utils") # fix me!
import redisdb

redisexpiretime = 60.*2  # move to config file 

def producer_f(singlewindow=False, use_rdkafka=False ):
    """
    Produces some random log files includeing user ID and timestamp using Kafka
    Parameters
    ----------
    singlewindow: True if you want to test the program
    use_rdkafka: set it True if you want to ingest more data 
    """
    tw = 1*60. # The time window in seconds
    nvfv = {'1'   :[0       , int(1e6), int(1e4)], # [0,   1e6): (forgetters)
            '5'   :[int(1e6), int(2e6), int(1e4)], # [1e6, 2e6): (login-logout) 
            '9'  :[int(2e6), int(3e6), int(1e4)], # [2e6, 3e6): (active-user)
            '1000' :[int(3e6), int(4e6), int(1)]} # [3e6, 4e6): (machine-spam)
    with open('../myconfigs.json', 'r') as f:
        myconfigs = json.load(f)
    # Set up the kafka clients. Here I have used 30 partitions and I am defining 3 working nodes as clients
    # Use hashed partitioner for balanced load distribution
    client   = KafkaClient(hosts=str(myconfigs["WORKERS_IP"]),zookeeper_hosts=str(myconfigs["MASTER_IP"]))
    topic    = client.topics[str(myconfigs["TOPIC"])]
    hash_partitioner = HashingPartitioner()
    producer = topic.get_producer(partitioner=hash_partitioner, linger_ms = 200, use_rdkafka=use_rdkafka)
    starttime = 0
    if singlewindow==True:
        starttime = produce_f(tw, nvfv, producer, starttime)
        print starttime
    else:
        while True:
            starttime = produce_f(tw, nvfv, producer, starttime)
            print starttime
            if (starttime % redisexpiretime) < 2:
                redisdb.set_expire_time(int(redisexpiretime))

def produce_f(tw, nvfv, producer, starttime):
    """
    Parameters
    ----------
    tw: time window in seconds
    nvfv: Input user groups
    producer: Kafka producer information
    starttime: start time
    """
    dtime = 0.
    nv = 0 # Initiate the number of the visits to the website during the time window
    ld = []
    for v in nvfv:
        nv += int(v)*nvfv[v][2]
        ld.append(np.repeat(np.random.randint(nvfv[v][0], nvfv[v][1], size=nvfv[v][2]), int(v))) 

    ld1 = np.concatenate(ld[:])
    np.random.shuffle(ld1)
    dt = tw/len(ld1)
    eventTime = 0
    delay = 0
    timedd = time.time()
    for index, item in enumerate(ld1):
        times = time.time()
        eventTime  += dt-delay # event time in Seconds
        currID = item
        outputStr = b"{};{}".format(currID, np.int64(np.floor(eventTime+starttime)*1e3)) # write the time in milliseconds
        isspider = redisdb.check_if_spider(str(currID))
        if isspider != str(True):
            producer.produce(outputStr, partition_key=str(currID))
        delay = (time.time()-times)
        #time.sleep(max(0.7*(dt-delay),1e-9))
    times = time.time()
    print time.time()-timedd
    return starttime + tw
    
if __name__ == '__main__':
    #process(sys.argv[1:])
    redisdb.flush_all_keys()
    producer_f()
    sys.exit(0)

