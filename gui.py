import PySimpleGUI
import requests

from core import settings

sg = PySimpleGUI
g_var = settings.global_var
api_model_info = {}
options = ['A', 'B']


def load_models():
    # create persistent session since we'll need to do a few API calls
    s = requests.Session()
    if g_var.api_auth:
        s.auth = (g_var.api_user, g_var.api_pass)

    # do a check to see if --gradio-auth is set
    r0 = s.get(g_var.url + '/sdapi/v1/cmd-flags')
    response_data = r0.json()
    if response_data['gradio_auth']:
        g_var.gradio_auth = True

    if g_var.gradio_auth:
        login_payload = {
            'username': g_var.username,
            'password': g_var.password
        }
        s.post(g_var.url + '/login', data=login_payload)
    else:
        s.post(g_var.url + '/login')

    all_models = s.get(g_var.url + "/sdapi/v1/sd-models")

    for model in all_models.json():
        api_model_info[model['title']] = model['model_name'], model['hash']


settings.startup_check()
load_models()

'''for model2 in api_model_info.items():
    print(model2[0])
    print(model2[1][0])
    print(model2[1][1])'''
first_value = list(api_model_info.values())[0]

sg.theme('DarkGrey2')
# define layout
left_column = [
    [sg.Text('Hi', justification='left')],
    [sg.Button('Back')]
]

right_column = [
    [sg.Text('Choose Model', size=(50, 1), justification='left')],
    [sg.Combo([str(x[0]) for x in api_model_info.items()], default_value=first_value, key='model', readonly=True)],
    [sg.Text('_' * 50)],
    [sg.Text('Choose', size=(30, 1),  justification='left')],
    [sg.Listbox(values=options, select_mode='extended', key='option', size=(30, 5), enable_events=True)],
    [sg.Button('Save'), sg.Button('Review'), sg.Button('Add C'), sg.Exit()]
]

layout = [
    [sg.Column(left_column),
     sg.VSeparator(),
     sg.Column(right_column)]
]

# Define Window
window = sg.Window('Manage data models', layout)
# Read values entered by user
while True:
    event, value = window.read()
    # access the selected value in the list box and add them to a string
    string = ''
    for v in value['option']:
        string = f"{string} {v},"
    if event == 'Save':
        sg.popup('Options Chosen',
                 f'You chose: {value["model"]}\nYour additional facilities are: {string[1:len(string) - 1]}')
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
