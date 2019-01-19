import os

tumblrsPath = '../blogs/'


def listBlogs(path = tumblrsPath):
    targets = []
    for e in os.scandir(path):
        for v in ['texts', 'images', 'answers', 'links']:
            if os.path.isfile(os.path.join(e.path, f'{v}.txt')) or os.path.isfile(os.path.join(e.path, f'{v}.json')):
                targets.append(e.name)
                break
    return targets
