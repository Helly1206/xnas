# -*- coding: utf-8 -*-
#########################################################
# SERVICE : params.py                                   #
#           Handles params and specific functions       #
#                                                       #
#           I. Helwegen 2020                            #
#########################################################

####################### IMPORTS #########################
import types
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################
class param:
    def __init__(self, key = None, value = ""):
        self.key = key
        self.value = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.key

    def key(self):
        return self.key

    def value(self):
        return self.value
#########################################################

#########################################################
# Class : params                                        #
#########################################################
class params:
    @classmethod
    def key(cls, item):
        ky = None
        if isinstance(item, param):
            ky = item.key
        return ky

    @classmethod
    def value(cls, item):
        val = None
        if isinstance(item, param):
            val = item.value
        else:
            val = item
        return val

    @classmethod
    def todict(cls):
        dct = {}
        for key, val in cls.__dict__.items():
            if not (key[:2] == "__" and key[-2:] == "__") and not isinstance(val, (types.FunctionType, type(None))):
                if isinstance(val, param):
                    dct[val.key] = val.value
                else:
                    dct[key] = val
        return dct

    @classmethod
    def tf(cls, val):
        return 'true' if cls.value(val) else 'false'

    @classmethod
    def yn(cls, val):
        return 'yes' if cls.value(val) else 'no'

    @classmethod
    def oz(cls, val):
        return '1' if cls.value(val) else '0'

    @classmethod
    def bl(cls, val):
        retval = False
        myval = cls.value(val)
        try:
            f = float(myval)
            if f > 0:
                retval = True
        except:
            if myval.lower() == "true" or myval.lower() == "yes" or myval.lower() == "1":
                retval = True
        return retval

    @classmethod
    def anyyn(cls, val):
        retval = False
        myval = cls.value(val)
        if type(myval) == bool:
            retval = "yes" if myval else "no"
        elif type(myval) == str:
            if myval.lower() == "true" or myval.lower() == "yes":
                retval = "yes"
            elif myval.lower() == "false" or myval.lower() == "no":
                retval = "no"
            else:
                retval = myval
        else:
            retval = myval
        return retval

    @classmethod
    def anybl(cls, val):
        retval = False
        myval = cls.value(val)
        if type(myval) == bool:
            retval = myval
        elif type(myval) == str:
            if myval.lower() == "true" or myval.lower() == "yes":
                retval = True
            elif myval.lower() == "false" or myval.lower() == "no":
                retval = False
            else:
                retval = myval
        else:
            retval = myval
        return retval

######################### MAIN ##########################
if __name__ == "__main__":
    pass
