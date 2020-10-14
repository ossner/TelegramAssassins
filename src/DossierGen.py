from Assassin import Assassin
import os
import random

# Random skills every assassin should totally have (especially seduction)
random_skills = ['lockpicking', 'hand-to-hand combat', 'target acquisition',
                 'covert operations', 'intelligence gathering', 'marksmanship',
                 'knife-throwing', 'explosives', 'poison', 'seduction',
                 'disguises', 'exotic weaponry', 'vehicles', 'disguise']

def compileDossier(assassin):
    # generates a pdf dossier with the information needed to assassinate the target
    template = open('latex\\template.tex', 'r').read()

    # replace all the placeholders
    template = template.replace('%_NAME_%', str(assassin.idgame) + '/' + str(assassin.chat_id))
    template = template.replace('%_REALNAME_%', removeUmlaut(assassin.name))
    template = template.replace('%_CODENAME_%', removeUmlaut(assassin.codename))
    template = template.replace('%_ADDRESS_%', removeUmlaut(assassin.address))

    # choosing random skills
    rand = random.randint(0, len(random_skills) - 1)
    rand2 = random.randint(0, len(random_skills) - 1)
    while rand == rand2:
        rand2 = random.randint(0, len(random_skills) - 1)

    template = template.replace('%_RANDOMSKILLONE_%', random_skills[rand])
    template = template.replace('%_RANDOMSKILLTWO_%', random_skills[rand2])
    template = template.replace('%_SPECIALIZATION_%', removeUmlaut(assassin.major))

    texName = str(assassin.idgame) + '\\' + str(assassin.chat_id)
    texDossier = open('dossiers\\' + texName + '.tex', "w")
    texDossier.write(template)
    texDossier.close()

    os.system('pdflatex -output-directory dossiers\\' + str(assassin.idgame) + ' dossiers\\' + texName + '.tex')

    os.system('del dossiers\\' + texName + '.aux')
    os.system('del dossiers\\' + texName + '.log')
    os.system('del dossiers\\' + texName + '.log')
    os.system('del dossiers\\' + texName + '.tex')


def removeUmlaut(string):
    u = 'ü'.encode()
    U = 'Ü'.encode()
    a = 'ä'.encode()
    A = 'Ä'.encode()
    o = 'ö'.encode()
    O = 'Ö'.encode()
    ss = 'ß'.encode()

    string = string.encode()
    string = string.replace(u, b'ue')
    string = string.replace(U, b'Ue')
    string = string.replace(a, b'ae')
    string = string.replace(A, b'Ae')
    string = string.replace(o, b'oe')
    string = string.replace(O, b'Oe')
    string = string.replace(ss, b'ss')

    string = string.decode('utf-8')
    return string