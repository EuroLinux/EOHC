#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import sys, readline
# import getpass, os

# def printPipe(pipe):
#     while 1:
#         line = pipe.readline()
#         if line:
#             print(line)
#         else:
#             return pipe.close()

# def echoResponse(response):
#     if self.echo:
#         sys.stdout.write("response: %s\n" % response)
#         sys.stdout.flush()
#     return response

def select(message, answers, selected=None):
    if not selected:
        selected = ""
    while True:
        readline.set_startup_hook(lambda: readline.insert_text(selected))
        try:
            print("\n" + message)
            for i in range(1,len(answers)+1):
                print("{0}. {1}".format(i, answers[i-1]))
            answer = input("Enter the choice number or the choice value: ")
            # Check if user entered the choice value
            if not answers or answer in answers:
                return answer

            # Check if user entered the choice number
            answer_srno = int(answer)
            if answer_srno in range(1,len(answers)+1):
                return answers[answer_srno-1]

            # otherwise
            print("\nPlease enter correct choice")
        except:
            print("\nPlease enter correct choice")
        finally:
            readline.set_startup_hook()

def prompt(message, validation=None, default=None, answers=None):
    # answers is deprecated - use select
    if answers:
        return select(message, answers)

    defaultValue = ""
    if default:
        defaultValue = default

    while True:
        readline.set_startup_hook(lambda: readline.insert_text(defaultValue))
        try:
            response = input(message)
            if response.strip():
                response
            # if there's a validation function, check it
            error = None
            if validation:
                error = validation(response.strip())
            if not error:
                return response.strip()

            sys.stdout.write(error + "\n")
        finally:
            readline.set_startup_hook()

def prompt_confirm(message):
    YES = "yes"
    SAMEASYES = ["y", "yes", "ya", "yup", "affirmative", "roger", "go", "t", "tak",
                 "engage", "whatever", "way", "si", "oui", "ja", "1", "true"]
    NO = "no"
    SAMEASNO = ["n", "no", "na", "nada" "negative", "negatory", "stop", "n", "nie",
                "never", "nooooo!", "no way", "non", "nein", "nicht", "0", "false"]
    message += " (%s|%s) " % (YES, NO)
    while True:
        answer = prompt(message)
        if answer.lower() in SAMEASYES:
            return True
        if answer.lower() in SAMEASNO:
            return False
        # otherwise
        sys.stdout.write("Please answer %s or %s.\n" %(YES, NO))

# def multiSelect(self, message, answers, selected=None):
#     if not selected:
#         selected = ""
#     while True:
#         readline.set_startup_hook(lambda: readline.insert_text(" ".join(selected)))
#         try:
#             selected_none = ('0', "None of these")
#             print("\n" + message)
#             print("{0}. {1}".format(*selected_none))
#             for i in range(1,len(answers)+1):
#                 print("{0}. {1}".format(i, answers[i-1]))
#             response = input("\n[Please enter either choice number(s) or the choice value(s)."
#             "If you are selecting more than one item then please make them comma separated]:\n")
#             if response in selected_none:
#                 return []
#             valid_choice_value = True
#             for choice_value in response.split(','):
#                 # Check if user entered the choice values
#                 if choice_value not in answers:
#                     valid_choice_value = False
#             if valid_choice_value:
#                 return response.split(',')

#             valid_choice_number = True
#             for choice_number in response.split(','):
#                 # Check if user entered the choice numbers
#                 choice_number = int(choice_number)
#                 if choice_number not in range(1,len(answers)+1):
#                     valid_choice_number = False

#             if valid_choice_number:
#                 return [answers[int(choice_number)-1] for choice_number in response.split(',')]
#             # otherwise
#             print("\nPlease enter correct choice")
#         except:
#             print("\nPlease enter correct choice")
#         finally:
#             readline.set_startup_hook()

# def promptPassword(self, message):
#     # no echo
#     return getpass.getpass(message)

# def statusMessage(self, message):
#     # always echo
#     sys.stdout.write(message)
#     sys.stdout.write("\n")
#     sys.stdout.flush()
#     return True

def prompt_integer(message, default=None):
    while True:
        sys.stdout.write(message)
        sys.stdout.flush()
        response = sys.stdin.readline()
        try:
            value = int(response.strip())
            return value
        except ValueError:
            sys.stdout.write("Please enter an integer.\n")

# def editText(self, message, default=None):
#     if default and '\n' in default:
#         return self.__editLargeText(message, default)
#     # otherwise - "small" default or no default
#     return self.prompt(message, validation=None, default=default)

# def promptFile(self, message):
#     """ prompt for the user to upload a file to the server transfer area """
#     while True:
#         sys.stdout.write(message+" ")
#         response = sys.stdin.readline()
#         print("\"%s\"" % response.strip())
#         if os.path.exists(response.strip()):
#             return response.strip()
#         # otherwise
#         print("Please enter a valid file path")
