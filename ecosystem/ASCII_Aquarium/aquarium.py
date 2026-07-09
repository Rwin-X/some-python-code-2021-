class Aquarium:
 def __init__(self,w,h):
  self.width=w; self.height=h; self.fishes=[]; self.objects=[]
 def add_fish(self,f): self.fishes.append(f)
 def add_object(self,o): self.objects.append(o)
 def update(self):
  [f.update(self) for f in self.fishes]
 def draw(self):
  g=[[" "]*self.width for _ in range(self.height)]
  [o.draw(g) for o in self.objects]
  [f.draw(g) for f in self.fishes]
  print("+"+"-"*self.width+"+")
  for r in g: print("|"+"".join(r)+"|")
  print("+"+"-"*self.width+"+")
