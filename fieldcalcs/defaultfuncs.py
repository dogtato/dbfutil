# -*- coding: utf-8 -*-
"""
Created on Sun Jun 30 20:07:08 2013

@author: chad
"""


def area(height, width):
    return height * width


# test comment
def concat(field1, field2):
    return str(field1) + ' ' + str(field2) + ' cats'


def halfstring(inputstr):
    strlen = len(inputstr)
    return  inputstr[:strlen / 2]
