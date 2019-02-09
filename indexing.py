import multiTumDis
import json
import os.path
import pandas

postTypes = ['texts', 'images', 'answers', 'links']

def main():
    M = multiTumDis.BackendManager('../blogs')
    for i, n in enumerate(M.names):
        print(i, f"{i/len(M.names) * 100:.3f}%", n, end ='\t')
        M.loadBlog(n)
        for pt in M['data-postTypes']:
            print(pt, end = '\t')
            fName = f"{pt}-index.json"
            M['data-postType'] = pt
            M['data-postTag'] = 'None'
            M['data-postIndex'] = 0
            M.currentBlogInfo.update(M.getDerivedInfos())
            with open(fName, 'a') as f:
                f.write(json.dumps({
                    'blog' : n,
                    'tags' : M['data-typeTags'],
                }))
                f.write('\n')

        print()

if __name__ == '__main__':
    main()
