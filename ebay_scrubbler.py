#!/usr/bin/python
#Last modified: Wed May 16, 2012  04:14PM

#this script is (C) 2012 Marco Guidetti
#marco@marcoguidetti.org

#Legalia:
#this script is released under GPL: http://www.gnu.org/licenses/gpl.html
#it is provided as-is without any kind of warranties, explicit or implicit.
#I take no responsibility of what you do with this script or part of it, or what
#might happen if you use it.
#So, just to be clear.

#to set it up:
#there are 3 things you need to do:
#1. and 2.
# in the function sendAMail() (just here below): set gmail_user and
# gmail_password as the username/password of the account you are using to send
# the mail. Do it as strings ("%s")
#3.
# do the same for the "to" variable in main. Also as a string.
#
#run it with 2 arguments:
#where you want to look for stuff and
#what you are looking for:
#python ebay_scrubbler.py bologna iphone
#python ebay_scrubbler.py milano "palm pre"
#or
#python ebay_scrubbler.py milano palm-pre
#(so to say).
#place it in your crontab, get mails (and filter them).

import smtplib
import os
import sys
import urllib
import bs4
import re
import robotparser

def sendAMail(to, subject, text, where, what):
#send a mail with the list of interesting classifieds
  gmail_user=False #as a string, please
  gmail_pwd=False  #as a string, please

  if gmail_user == False or gmail_pwd == False:
    print "please, provide me with the credentials to access a gmail account in the source file, inside the function sendAMail"
    sys.exit(1)

  sender="Annunci nuovi <%s>"%gmail_user
  
  msg="From: %s\r\nTo: %s\r\nSubject: %s\r\nX-Mailer: python\r\n\r\n" % (sender, to, subject)
  msg=msg+text+"\n\n\n the keyword with which I was invoked were \"%s\" for where and  \"%s\" for what"%(where, what)

  mailServer = smtplib.SMTP("smtp.gmail.com", 587)
  mailServer.ehlo()
  mailServer.starttls()
  mailServer.ehlo()
  mailServer.login(gmail_user, gmail_pwd)
  mailServer.sendmail(gmail_user, to, msg )
  mailServer.close()

  return

def buildAddress(where, what, page=False):
#build the address, in this way we do not need to search
#TODO:we are not yet using the page stuff, the point is to decide how much
#back in time we want to go when first looking (or searching afterwards)
  baseAddress="http://annunci.ebay.it/"#annunci-bologna/ipad/
  if not page:
    address=baseAddress+"annunci-"+where+"/"+what
  else:
    address=baseAddress+"annunci-"+where+"/"+what+"?p="+page
  return address

def fetchPage(address):
#get the page!
  link=urllib.urlopen(address)
  page=link.read()
  return page

def isPayPal(slist):
#are we looking at a paypal-enable classified?
  if slist[16].lower().find("paypal") != -1 or slist[18].lower().find("paypal") != -1:
    #print " i am in is is Paypal and ispaypal is True"
    return True
  else:
    return False

def isHighlight(slist):
#is the ad with highlight?
  if slist[16].lower().find("evidenza") != -1:
    return True
  else:
    return False

#these 3 functions are a bit of yaddayadda looking at the pieces of the
#strings. Sometimes there are ways to make it better without regexp ;)
def getClassifiedLink(slist):
#get the link of the ad
  rough=slist[3]
  m=re.search('\"(.*?)\"',rough).group(1)
  return m

def getClassifiedDescription(slist):
#get the Description (which really is not the title)
  rough=slist[12].replace("\n"," ")
  nsrough=rough.split('>')[1]
  return nsrough

def getClassifiedPrice(slist, ispaypal=False, ishighlight=False):
#not very nice, since the price depends on the fact that we are with paypal,
#with highlight or both.
  if ispaypal and ishighlight:
    rough=slist[21]
    return rough.split('>')[1].split()[0]
  elif ispaypal and not ishighlight:
    rough=slist[19]
    return rough.split('>')[1].split()[0]
  elif not ispaypal and ishighlight:
    rough=slist[19]
    return rough.split('>')[1].split()[0]
  else:
    rough=slist[17]
    return rough.split('>')[1].split()[0]

def getResults(where,what,page=False):
  #we build the ebay annunci address, he does the search for us
  if not page:
    address=buildAddress(where,what)
  else:
    address=buildAddress(where,what,page)
  #and then we prepare the soup with BS4
  soup=bs4.BeautifulSoup(fetchPage(address))
  #and we get the result array, search for the right (!) <div>
  results=soup.find_all('div', 'searchResultListItem row')
  aresults=[]
  parseResults(results,aresults)
  return aresults

def areWeNew(where,what):
#is the search a new one?
  if os.path.exists("./.%s-%s.last"%(where,what)):
    return False
  else:
    return True

def createLastFile(where,what,aresults):
#we take the most recent one and write it down, so that we do not overlap
#results
  f=open(".%s-%s.last"%(where,what),"w")
  for elem in range(len(aresults[0])):
    f.write(str(aresults[0][elem])+"\n")
  f.close()
  return

def readLastFile(where,what):
#we read the file we wrote with the info of the last search
  f=open(".%s-%s.last"%(where,what),"r")
  lines=f.readlines()
  f.close()
  elems=[]
  for i in range(len(lines)):
    elems.append(lines[i].strip())
  return elems

def parseResults(results,aresults):
#using some logic we parse the results and put them inside a nice list
  for i in range(len(results)):
    string=str(results[i])
    slist=string.strip().split('<')
    item=[]
    if isPayPal(slist):
      item.extend([1, getClassifiedLink(slist), getClassifiedDescription(slist), getClassifiedPrice(slist, ispaypal=isPayPal(slist), ishighlight=isHighlight(slist))])
    else:
      item.extend([0, getClassifiedLink(slist), getClassifiedDescription(slist), getClassifiedPrice(slist, ispaypal=isPayPal(slist), ishighlight=isHighlight(slist))])
    aresults.append(item)
  return

def formatText(results):
#given the results, we format it to be sent by mail
  textLine='%s \n %s euro -> %s\n'
  finalString=""
  for elem in results:
    string="".join(textLine%(elem[2], elem[3], elem[1]))
    finalString=finalString+string+"\n"
  return finalString


def findLastOneOnline(lastEntry):
#we look for the lastEntry in the results we have from the 'net. If it's there,
#then we are going to return it's index, so that we can consider only the ones we
#don't have yet
  temporaryResults=getResults(where,what)
  for i in range(len(temporaryResults)):
    if temporaryResults[i][1] == lastEntry[1]:
      break
  return i

if __name__ == '__main__':
#command line arguments
  if len(sys.argv)<3:
    print "please provide where and what. you can use " " to join more words in the what"
    print "or be clever and join them yourself with the -"
    sys.exit(1)
  where=sys.argv[1]
  what=sys.argv[2]
#if the second argument contains more than one thing, join them with a -
  if len(what.split()) > 1:
    what= "-".join(what.split())

  to = False # as a string, please
  if to == False:
    print "modify the code so that to contains a valid destination mail address"
    sys.exit(1)
  #we check this file before seeing that we can fetch stuff
  rp=robotparser.RobotFileParser()
  rp.set_url("http://annunci.ebay.it/robots.txt")
  rp.read()
  if not rp.can_fetch("*",buildAddress(where,what)):
    print "we shouldn\'t be doing this!" 
    sys.exit(1)

  if areWeNew(where,what):
    results=getResults(where,what)
    createLastFile(where,what,results)
    content=formatText(results)
    sendAMail(to , "new ads for %s in %s" % (what, where), content,where, what)
    print "sent"
  else:
    lastEntry=readLastFile(where,what)
    whereLastIs=findLastOneOnline(lastEntry)
    if int(whereLastIs)==0:
      print "nothing new"
      sys.exit(0)
    else:
      results=getResults(where,what)
      results=results[:whereLastIs]
      createLastFile(where, what, results)
      content=formatText(results)
      sendAMail(to , "differential in ads for %s in %s" % (what,where), content, where, what)
      print "sent"
   


