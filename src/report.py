import os
import glob
import parsable
parsable = parsable.Parsable()
import pomagma.util


DATA = pomagma.util.DATA


@parsable.command
def conjectures(theory):
    '''
    Write conjectures.html
    '''
    in_pattern = os.path.join(DATA, 'atlas', theory, '*conjectures*.facts')
    conjectures_files = list(glob.glob(in_pattern))
    assert conjectures_files, 'found no conjectures to report'
    conjectures_html = os.path.join(DATA, 'report', theory, 'conjectures.html')
    destin = os.path.dirname(conjectures_html)
    if not os.path.exists(destin):
        os.makedirs(destin)
    with open(conjectures_html, 'w') as html:
        html.write(
            '''
            <html>
            <head>
            <title> Pomagma {theory} Conjectures </title>
            </head>
            <body>
            '''.format(theory=theory)
        )
        for conjectures_file in conjectures_files:
            with open(conjectures_file) as conjectures:
                html.write('<p><pre>\n')
                html.write(conjectures.read())
                html.write('</pre></p>\n')
        html.write(
            '''
            </body>
            </html>
            '''
        )


if __name__ == '__main__':
    parsable.dispatch()
