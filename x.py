import mysql.connector

mydb = mysql.connector.connect(host = 'localhost', user = 'root', password = 'root', database = 'Diary')

m = mydb.cursor()

# m.execute("CREATE DATABASES Diary")

# m.execute("SHOW DATABASES")
# for i in m:
#     print(i)

# m.execute("CREATE TABLE Users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) NOT NULL, email VARCHAR(255) NOT NULL UNIQUE, password VARCHAR(255) NOT NULL)")

# s = "insert into Users (name,email,password) values (%s, %s, %s)"

# val = [
#     ('Dhyey','dhyeybhatt66@gmail.com', 'Dhyey3010'),
#     ('Aim','aim69@gmail.com','123')
# ]

# m.executemany(s,val)

# print(m.rowcount)

# mydb.commit()

m.execute("select * from users")
# m.execute("select name from users")

# rows = m.fetchone()
rows = m.fetchall()


for r in rows:
    print(r)
