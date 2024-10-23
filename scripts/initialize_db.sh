#!/bin/bash

# Assign command line arguments to variables
RDS_ENDPOINT=$1
RDS_USERNAME=$2
RDS_PASSWORD=$3

# Create tables in the MySQL database
mysql -h "$RDS_ENDPOINT" -P 3306 -u "$RDS_USERNAME" -p"$RDS_PASSWORD" assistant -e "CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL
);"

mysql -h "$RDS_ENDPOINT" -P 3306 -u "$RDS_USERNAME" -p"$RDS_PASSWORD" assistant -e "CREATE TABLE IF NOT EXISTS meetings (
  meeting_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  description TEXT
);"

mysql -h "$RDS_ENDPOINT" -P 3306 -u "$RDS_USERNAME" -p"$RDS_PASSWORD" assistant -e "CREATE TABLE IF NOT EXISTS meeting_participants (
  meeting_id INT,
  email VARCHAR(255),
  PRIMARY KEY (meeting_id, email),
  FOREIGN KEY (meeting_id) REFERENCES meetings (meeting_id),
  FOREIGN KEY (email) REFERENCES users (email)
);"

# Load data from CSV files
mysql --local-infile=1 -h "$RDS_ENDPOINT" -P 3306 -u "$RDS_USERNAME" -p"$RDS_PASSWORD" assistant -e "LOAD DATA LOCAL INFILE '../input/users.csv' INTO TABLE users FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES (name, email);"

mysql --local-infile=1 -h "$RDS_ENDPOINT" -P 3306 -u "$RDS_USERNAME" -p"$RDS_PASSWORD" assistant -e "LOAD DATA LOCAL INFILE '../input/meetings.csv' INTO TABLE meetings FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES (title, start_time, end_time, description);"

mysql --local-infile=1 -h "$RDS_ENDPOINT" -P 3306 -u "$RDS_USERNAME" -p"$RDS_PASSWORD" assistant -e "LOAD DATA LOCAL INFILE '../input/meeting_participants_v2.csv' INTO TABLE meeting_participants FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n' IGNORE 1 LINES (meeting_id, email);"
