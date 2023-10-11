install_python_packages(){
    pip install --root-user-action=ignore --upgrade pip
    pip install --root-user-action=ignore -r requirements.txt
}

configure_git(){

    if [[ ! -z $GIT_USER_NAME && ! -z $GIT_EMAIL && ! -z $GIT_COMMIT_EDITOR ]]
    then
        git config --global user.name "$GIT_USER_NAME"
        git config --global user.email "$GIT_EMAIL"
        git config --global --replace-all core.editor "$GIT_COMMIT_EDITOR"
    else
        echo "Skipping git configuration, one or more GIT variable is not set"
    fi
}


main(){
    install_python_packages
    configure_git
}

main