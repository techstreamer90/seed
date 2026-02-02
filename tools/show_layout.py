import json

data = json.load(open('model/sketch.json'))
nodes = sorted(data['nodes'], key=lambda n: (n['y'], n['x']))

print('\nVISUAL LAYOUT (4-column grid, 350px spacing):\n')
curr_y = None
for n in nodes:
    if curr_y != n['y']:
        print()
        curr_y = n['y']
    print(f'{n["id"]:45s}', end=' ')
print('\n')
