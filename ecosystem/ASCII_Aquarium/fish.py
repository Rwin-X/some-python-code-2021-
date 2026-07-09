class Fish:
 def __init__(self,x,y,d=1):
  self.x=x; self.y=y; self.d=d
 def update(self,aq):
  self.x+=self.d
  if self.x>=aq.width-3: self.d=-1
  if self.x<=0: self.d=1
 def draw(self,g):
  s="><>" if self.d>0 else "<><"
  for i,c in enumerate(s):
   x=self.x+i
   if 0<=x<len(g[0]): g[self.y][x]=c
