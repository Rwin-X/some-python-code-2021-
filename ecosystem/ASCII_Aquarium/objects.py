class Plant:
 def __init__(self,x,b): self.x=x; self.b=b
 def draw(self,g):
  for y in range(max(0,self.b-3),self.b+1): g[y][self.x]="Y"
class Rock:
 def __init__(self,x,y): self.x=x; self.y=y
 def draw(self,g): g[self.y][self.x]="O"
