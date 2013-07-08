import parsable
import pomagma.editor.app


parsable.command(pomagma.editor.app.serve)


if __name__ == '__main__':
    parsable.dispatch()
