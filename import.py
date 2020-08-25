from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,scoped_session
import os,csv

engine=create_engine("postgres://swgbwjngevunld:0ca53e5f8a2ace6a543273836b975bb733862f5374aaddfe2ce7659db126afca@ec2-52-44-55-63.compute-1.amazonaws.com:5432/dc2tof4iv20q6i")
db=scoped_session(sessionmaker(bind=engine))

file=open("books.csv")
reader=csv.reader(file)

for isbn,title,author,year in reader:
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
               {"isbn": isbn,
                "title": title,
                "author": author,
                "year": year})

    print(f"Added book {title} to database.")

    db.commit()