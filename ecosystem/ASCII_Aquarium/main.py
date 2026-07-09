import os,time
from aquarium import Aquarium
from fish import Fish
from objects import Plant,Rock
aq=Aquarium(60,20)
aq.add_fish(Fish(5,10))
aq.add_fish(Fish(30,5,-1))
aq.add_object(Plant(8,19))
aq.add_object(Plant(50,19))
aq.add_object(Rock(25,18))
while True:
 os.system("cls" if os.name=="nt" else "clear")
 aq.update(); aq.draw(); time.sleep(0.1)
