
morse_crachters = {

    'a':'.-',#1000,500| 200,1000
    'b':'-...',#200,1000|1000,500|1000,500|1000,500
    'c':'-.-.',#200,1000|1000,500|200,1000|1000,500
    'd':'-..',#200,1000|1000,500|1000,500
    'e':'.',#1000,500
    'f':'..-.',#1000,500|1000,500|200,1000|1000,500
    'g':'--.',#200,1000|200,1000|1000,500
    'h':'....',#1000,500|1000,500|1000,500|1000,500
    'i':'..',#1000,500|1000,500
    'j':'.---',#1000,500|200,1000|200,1000|200,1000
    'k':'-.-',#200,1000|1000,500|200,1000
    'l':'.-..',#1000,500|200,1000|1000,500|1000,500
    'm':'--',#200,1000|200,1000
    'n':'-.',#200,1000|1000,500
    'o':'---',#200,1000|200,1000|200,1000
    'p':'.--.',#1000,500|200,1000|200,1000|1000,500
    'q':'--.-',#200,1000|200,1000|1000,500|200,1000
    'r':'.-.',#1000,500|200,1000|1000,500
    's':'...',#1000,500|1000,500|1000,500
    't':'-',#200,1000
    'u':'..-',#1000,500|1000,500|200,1000
    'v':'...-',#1000,500|1000,500|1000,500|200,1000
    'w':'.--',#1000,500|200,1000|200,1000
    'x':'-..-',#200,1000|1000,500|1000,500|200,1000
    'y':'-.--',#200,1000|1000,500|200,1000|200,1000
    'z':'--..',#200,1000|200,1000|1000,500|1000,500
    '1':'.----',#1000,500|200,1000|200,1000|200,1000|200,1000
    '2':'..---',#1000,500|1000,500|200,1000|200,1000|200,1000
    '3':'...--',#1000,500|1000,500|1000,500|200,1000|200,1000
    '4':'....-',#1000,500|1000,500|1000,500|1000,500|200,1000
    '5':'.....',#1000,500|1000,500|1000,500|1000,500|1000,500
    '6':'-....',#200,1000|1000,500|1000,500|1000,500|1000,500
    '7':'--...',#200,1000|200,1000|1000,500|1000,500|1000,500
    '8':'---..',#200,1000|200,1000|200,1000|1000,500|1000,500
    '9':'----.',#200,1000|200,1000|200,1000|200,1000|1000,500
    '0':'-----'#200,1000|200,1000|200,1000|200,1000|200,1000

}

morse_crachters_de = {
    '.-':'a',
    '-...':'b',
    '-.-.':'c',
    '-..':'d',
    '.':'e',
    '..-.':'f',
    '--.':'g',
    '....':'h',
    '..':'i',
    '.---':'j',
    '-.-':'k',
    '.-..':'l',
    '--':'m',
    '-.':'n',
    '---':'o',
    '.--.':'p',
    '--.-':'q',
    '.-.':'r',
    '...':'s',
    '-':'t',
    '..-':'u',
    '...-':'v',
    '.--':'w',
    '-..-':'x',
    '-.--':'y',
    '--..':'z',
    '.----':'1',
    '..---':'2',
    '...--':'3',
    '....-':'4',
    '.....':'5',
    '-....':'6',
    '--...':'7',
    '---..':'8',
    '----.':'9',
    '-----':'0',
}

from winsound import Beep
from time import sleep


class mord:
    def morse_co(vorodi):
        vorodi = list(vorodi)
        total = []
        for i in vorodi:
            if i == 'a' or i =='A':
                total.append(morse_crachters['a'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
            elif i == 'b' or i =='B':
                total.append(morse_crachters['b'])
                sleep(2)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
            elif i == 'c' or i =='C':
                total.append(morse_crachters['c'])
                sleep(2)
                Beep(200,1000)
                Beep(1000,500)
                Beep(200,1000)
                Beep(1000,500) 
            elif i == 'd' or i == 'D':
                total.append(morse_crachters['d'])
                sleep(2) 
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
            elif i == 'e' or i == 'E':
                total.append(morse_crachters['e'])
                sleep(2)
                Beep(1000,500)
            elif i == 'f' or i == 'F':
                total.append(morse_crachters['f']) 
                sleep(2) 
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
                Beep(1000,500)
            elif i == 'g' or i == 'G':
                total.append(morse_crachters['g'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
            elif i == 'h' or i == 'H':
                total.append(morse_crachters['h'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
            elif i == 'i' or i == 'I':
                total.append(morse_crachters['i'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
            elif i == 'j' or i == 'J':
                total.append(morse_crachters['j'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
            elif i == 'k' or i == 'K':
                total.append(morse_crachters['k'])
                sleep(2) 
                Beep(200,1000)
                Beep(1000,500)
                Beep(200,1000)
            elif i == 'l' or i == 'L':
                total.append(morse_crachters['l'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
            elif i == 'm' or i == 'M':
                total.append(morse_crachters['m'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
            elif i == 'n' or i == 'N':
                total.append(morse_crachters['n'])
                sleep(2)
                Beep(200,1000)
                Beep(1000,500)
            elif i == 'o' or i == 'O':
                total.append(morse_crachters['o'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
            elif i == 'p' or i == 'P':
                total.append(morse_crachters['p'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
            elif i == 'q' or i == 'Q':
                total.append(morse_crachters['q'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
                Beep(200,1000)
            elif i == 'r' or i == 'R':
                total.append(morse_crachters['r'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
                Beep(1000,500)
            elif i == 's' or i == 'S':
                total.append(morse_crachters['s'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
            elif i == 't' or i == 'T':
                total.append(morse_crachters['t'])
                sleep(2)
                Beep(200,1000)
            elif i == 'u' or i == 'U':
                total.append(morse_crachters['u'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
            elif i == 'v' or i == 'V':
                total.append(morse_crachters['v'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
            elif i == 'w' or i == 'W':
                total.append(morse_crachters['w'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)
            elif i == 'x' or i == 'X':
                total.append(morse_crachters['x'])
                sleep(2)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
            elif i == 'y' or i == 'Y':
                total.append(morse_crachters['y']) 
                sleep(2) 
                Beep(200,1000)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)          
            elif i == 'z' or i == 'Z':
                total.append(morse_crachters['z'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
            elif i == '1':
                total.append(morse_crachters['1'])
                sleep(2)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
            elif i == '2':
                total.append(morse_crachters['2'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
            elif i == '3':
                total.append(morse_crachters['3'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
                Beep(200,1000)
            elif i == '4':
                total.append(morse_crachters['4'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(200,1000)
            elif i == '5':
                total.append(morse_crachters['5'])
                sleep(2)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500) 
            elif i == '6':
                total.append(morse_crachters['6'])
                sleep(2)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)
            elif i == '7':
                total.append(morse_crachters['7']) 
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
                Beep(1000,500)          
            elif i == '8':
                total.append(morse_crachters['8'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
                Beep(1000,500)
            elif i == '9':
                total.append(morse_crachters['9'])
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
                Beep(1000,500)
            elif i == '0':
                total.append(morse_crachters['0']) 
                sleep(2)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)
                Beep(200,1000)   
            elif i == " ":
                total.append("|") 
                sleep(4)   
         
        print('< : this is used to separate each letter')
        print('| : this is used to separate each word')
        return(' '.join(total))

 ##############################################################################


    def morse_de_co(vorodi_2):
        vorodi_2 = str(vorodi_2)
        vorodi_2 = vorodi_2.split()
        total_2 = []
        for i in vorodi_2:
            if i =='.-':
                total_2.append(morse_crachters_de['.-'])#a
            elif i =='-...':
                total_2.append(morse_crachters_de['-...'])#b
            elif i =='-.-.':
               total_2.append(morse_crachters_de['-.-.'])#c    
            elif i =='-..':
               total_2.append(morse_crachters_de['-..'])#d
            elif i =='.':
               total_2.append(morse_crachters_de['.'])# e  
            elif i =='..-.':
               total_2.append(morse_crachters_de['..-.'])#f   
            elif i =='--.':
               total_2.append(morse_crachters_de['--.'])#g
            elif i =='....':
               total_2.append(morse_crachters_de['....'])#h
            elif i =='..':
               total_2.append(morse_crachters_de['..'])#i
            elif i =='.---':
               total_2.append(morse_crachters_de['.---'])#j
            elif i =='-.-':
               total_2.append(morse_crachters_de['-.-'])#k
            elif i =='.-..':
               total_2.append(morse_crachters_de['.-..'])#l
            elif i =='--':
               total_2.append(morse_crachters_de['--'])#m
            elif i =='-.':
               total_2.append(morse_crachters_de['-.'])#n
            elif i =='---':
               total_2.append(morse_crachters_de['---'])#o
            elif i =='.--.':
               total_2.append(morse_crachters_de['.--.'])#p
            elif i =='--.-':
               total_2.append(morse_crachters_de['--.-'])#q
            elif i =='.-.':
               total_2.append(morse_crachters_de['.-.'])#r
            elif i =='...':
               total_2.append(morse_crachters_de['...'])#s
            elif i =='-':
               total_2.append(morse_crachters_de['-'])#t
            elif i =='..-':
               total_2.append(morse_crachters_de['..-'])# u     
            elif i =='...-':
               total_2.append(morse_crachters_de['...-'])#v
            elif i =='.--':
               total_2.append(morse_crachters_de['.--'])#w
            elif i =='-..-':
               total_2.append(morse_crachters_de['-..-'])#x
            elif i =='-.--':
               total_2.append(morse_crachters_de['-.--'])#y   
            elif i =='--..':
               total_2.append(morse_crachters_de['--..'])#z
            elif i =='.----':
               total_2.append(morse_crachters_de['.----'])#1
            elif i =='..---':
               total_2.append(morse_crachters_de['..---'])#2
            elif i =='...--':
               total_2.append(morse_crachters_de['...--'])#3
            elif i =='....-':
               total_2.append(morse_crachters_de['....-'])# 4     
            elif i =='.....':
               total_2.append(morse_crachters_de['.....'])#5
            elif i =='-....':
               total_2.append(morse_crachters_de['-....'])#6   
            elif i =='--...':
               total_2.append(morse_crachters_de['--...'])#7
            elif i =='---..':
               total_2.append(morse_crachters_de['---..'])#8
            elif i =='----.':
               total_2.append(morse_crachters_de['----.'])#9
            elif i =='-----':
               total_2.append(morse_crachters_de['-----'])#0
            elif i == ' ':
                continue
            elif i =='|':
                total_2.append(' ')   
        return(''.join(total_2))    




####!##################################################################################################################################################
print(" chose your favorite translate :")
print(" A: morse \n B: byte ")

chose = input("A or B : ")

if chose =="a" or chose == "A":
    test = input("ENTER A TXT : ")

    print(mord.morse_co(test))

    print("do yo like have translete morse to txt :")
    porsesh1 = input(" y or n :")

    if porsesh1 =="y" or porsesh1 =="Y":

        test2 = input("enter morse :")
        print(mord.morse_de_co(test2))
    elif porsesh1 == "n" or porsesh1=="N":
        print("")
        
            
else :
    porsesh = input("enter txt:")
    farakhani =mord.morse_co(porsesh)
    tabdil = list(farakhani)
    total = []
    for chars in tabdil:
        if chars =="-":
            total.append("1")
        elif chars ==".":
            total.append("0")
        else:
            total.append(" ")
    print("".join(total))

#####?############################################################################################################################################            
    r_porsesh_2 = input("enter binari to translate :")
    #r_farakhani_2 = mord.morse_de_co(r_porsesh_2)
    r_tabdil_2 = list(r_porsesh_2)
    r_total_2 = []
    for r_chars in r_tabdil_2:
        if r_chars =="1":
            r_total_2.append("-")
        elif r_chars =="0":
            r_total_2.append(".")
        else:
            r_total_2.append(" ")    
    r_total_2 = "".join(r_total_2)
    ending = mord.morse_de_co(r_total_2)
    

               


      

####!###############################################################################################################################################






# import qrcode 

# end_work = qrcode.make(mord.morse_co(test))
# end_work.save("your morse qr.jpg")
