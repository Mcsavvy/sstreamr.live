source sstreamr/bin/activate
alias runserver="python3 manage.py runserver 0.0.0.0:8000"
alias rungunicorn="gunicorn Sstreamr.wsgi:application -b 0.0.0.0:8000"
alias runtests="python3 manage.py tests"
alias migrations="python3 manage.py makemigrations"
alias migrate="python3 manage.py migrate"
alias shell="python3 manage.py shell"
alias manage="python3 manage.py"
export PATH=sstreamr/bin:$PATH
