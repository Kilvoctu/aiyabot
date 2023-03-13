import PySimpleGUI
import subprocess
import sys

from core import settings

sg = PySimpleGUI
g_var = settings.global_var
api_model_info = {}
options = ['A', 'B']


# This function does the actual "running" of the command.  Also watches for any output. If found output is printed
def console_log(cmd, timeout=None, window=None):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ''
    for line in p.stdout:
        line = line.decode(errors='replace' if sys.version_info < (3, 5) else 'backslashreplace').rstrip()
        output += line
        print(line)
        window.Refresh() if window else None
    retval = p.wait(timeout)
    return retval, output


def load_models():
    s = settings.authenticate_user()

    all_models = s.get(g_var.url + "/sdapi/v1/sd-models")

    for model in all_models.json():
        api_model_info[model['title']] = model['model_name'], model['hash']


settings.startup_check()
settings.files_check()
settings.populate_global_vars()
load_models()
first_value = list(api_model_info.values())[0]

model_names = []
for m_key, m_value in settings.global_var.model_info.items():
    model_names.append(m_key)


def main():
    sg.theme('DarkGrey2')
    # define layout
    menu_def = [
        ['&File', ['Launch AIYA', '---', 'E&xit']],
        ['&Edit', ['Cut', 'Copy', 'Paste', 'Undo']],
        ['&View', ['Main', 'Loaded models']],
        ['&Help', ['Test', ['Test1', 'Test2'], 'About']]
    ]

    right_click_menu = ['Unused', ['Launch AIYA', '---', 'View',
                                   ['Main', 'Loaded models'], 'Exit']]
    input_right_click = ['Unused', ['Cut', 'Copy', 'Paste', 'Undo']]

    button_column = [
        [sg.Button('Save'), sg.Button('Review'), sg.Button('Add C')],
    ]

    button_column_col2 = [
        [sg.Button('Edit')],
    ]

    main_screen = [
        [sg.Text('Choose model', size=(60, 1), justification='left')],
        [sg.Combo([str(x[0]) for x in api_model_info.items()], default_value=first_value, key='model', expand_x=True, readonly=True)],
        [sg.HSeparator()],
        [sg.Text('Choose', size=(30, 1), justification='left')],
        [sg.Listbox(values=options, select_mode='extended', key='option', size=(60, 5), expand_x=True, expand_y=True, enable_events=True)],
    ]

    loaded_models = [
        [sg.Text('Display name', justification='left')],
        [sg.Listbox(values=model_names, select_mode='extended', key='model_names',
                    expand_x=True, expand_y=True, enable_events=True)],
    ]

    layout = [
        [sg.Menu(menu_def)],
        [sg.Column(main_screen, key='COL1', expand_x=True, expand_y=True),
         sg.Column(loaded_models, key='COL2', expand_x=True, expand_y=True, visible=False)],
        [sg.Column(button_column, key='COL1b', justification='center'),
         sg.Column(button_column_col2, key='COL2b', justification='center', visible=False)],
        [sg.HSeparator()],
        [sg.Text('Console log', justification='left')],
        [sg.Input(key='console_in', visible=False)],
        [sg.Output(key='console_out', size=(60, 7), expand_x=True)],
    ]

    # Define Window
    window = sg.Window('Manage data models', layout, size=(800, 400), right_click_menu=right_click_menu, resizable=True, finalize=True)
    window.bind('<Configure>', "Event")
    column = 1
    column1, column1b = window['COL1'], window['COL1b']
    column2, column2b = window['COL2'], window['COL2b']
    # Read values entered by user
    while True:
        event, value = window.read()
        console_log(cmd=value['console_in'], window=window)
        # access the selected value in the list box and add them to a string
        string = ''
        for v in value['option']:
            string = f"{string} {v},"
        if event == 'Save':
            sg.popup('Options Chosen',
                     f'You chose: {value["model"]}\nLook at these letters: {string[1:len(string) - 1]}')
        if event == 'Review':
            model_list = ''
            for name in api_model_info.items():
                model_list += f'{name[1][0]}\n'
            sg.popup_scrolled(model_list, size=(50, 20))
        if event == 'Add C':
            options.append('C')
            window['option'].update(options)
            print(options)
        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        if event == 'Launch AIYA':
            print("This doesn't work yet!")
        if event == 'Main' and column != 1:
            column = 1
            column1b.update(visible=True)
            column2b.update(visible=False)
            column1.update(visible=True)
            column2.update(visible=False)
            print('Showing main screen')
        if event == 'Loaded models' and column != 2:
            column = 2
            column1b.update(visible=False)
            column2b.update(visible=True)
            column1.update(visible=False)
            column2.update(visible=True)
            print('Showing loaded models')
        if event == 'Test':
            for model2 in api_model_info.items():
                print(f'model2[0] is {model2[0]}')
                print(f'model2[1][0] is {model2[1][0]}')
                print(f'model2[1][1] is {model2[1][1]}')

        if event == "Event":
            print(window.size)

        if event == 'Cut':
            print("You grabbed a pair scissors!")
        if event == 'Copy':
            print("Hello!")
            print("\"Hello!\" I copied it!")
        if event == 'Paste':
            print("I pasted.... nothing!")
        if event == 'Undo':
            print("I can't do that!")


if __name__ == '__main__':
    main()
