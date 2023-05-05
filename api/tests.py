import multiprocessing
from django.utils import timezone
class SummingProcess(multiprocessing.Process):
     def __init__(self,low,high):
         super().__init__()
         self.low=low
         self.high=high
         self.total=0

     def run(self):
         for i in range(self.low,self.high):
             self.total+=i


thread1 = SummingProcess(0,500000)
thread2 = SummingProcess(500000,1000000)
start = timezone.now()
thread1.start() # This actually causes the thread to run
thread2.start()
thread1.join()  # This waits until the thread has completed
thread2.join()
# At this point, both threads have completed
result = thread1.total + thread2.total
print((timezone.now()-start).total_seconds())
print(result)


start = timezone.now()
total = 0
for i in range(0,1000000):
    total+=i
print((timezone.now()-start).total_seconds())
print(total)
