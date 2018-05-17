import shutil
import os

REPO_NAME = 'asf_api_assistant'
GET_ASF_REPO = 'https://github.com/asfadmin/{}.git'.format(REPO_NAME)


def install():
    print(os.path.isdir(REPO_NAME))
    if not os.path.isdir(REPO_NAME):
        clone_repo()

    move_scipts()

def clone_repo():
    os.system('git clone {}'.format(GET_ASF_REPO))



def move_scipts():
    script = 'get_asf.py'
    get_asf_path = os.path.join('asf_api_assistant', 'src', script)
    deps_path = 'granule_lib/deps'

    make_if_not_there(deps_path)

    shutil.copy(
        get_asf_path,
        os.path.join(deps_path, script)
    )


def make_if_not_there(path):
    try:
        os.makedirs(path)
    except:
        pass


if __name__ == "__main__":
    install()
