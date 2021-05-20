<h2 align="center"> Influencer Detector on Twitter 📢</h2>

<p align="center">
  <img src="https://github.com/luisblazquezm/influencer-detection/blob/main/doc/resources/img/demo.gif?raw=true?raw=true" hspace="20">
</p>

##  📲 Introduction

This is a project consisting on the extraction of tweets from users on Twitter where, applying a normalized metric, will result on the detection of possible influencers and people on social media that could help brands sell and promote their products

## 💻 Structure

This is a high abstraction level representation of the architecture implemented:

<p align="center">
  <img src="https://github.com/luisblazquezm/influencer-detection/blob/main/doc/resources/img/Arquitectura.jpg?raw=true" hspace="20">
</p>

* ``api`` : contains the PHP files for frontend and backend functionality following Model View Controller pattern.
* ``doc`` : contains adittional files and content for web development (images, css, js, ...).
* ``web`` : documentation built with **Sphinx** that details the structure of the code (classes, methods, functions, ...) in the [main_analysis](https://github.com/bisite/SocialBrandAnalysis/tree/master/src/metrics/main_analysis) folder

## 🛠 Installation

Main appliance and tools to install:
```bash
sudo apt update
sudo apt install python3 python3-pip nodejs libpq-dev -y
sudo npm install -g pm2
```

Python API can be launched with the launch script in /influencer-detection/src/api:
```
sudo bash launch.bash
```

Node server instance will be launch in /web:
```
sudo npm start
```

## 👥 Authors
<table>
<tr>
    <td align="center"><a href="https://github.com/luisblazquezm"><img src="https://avatars0.githubusercontent.com/u/40697133?s=460&u=82f3e7d01e88b27ea481e57791fa62c9d519d2ac&v=4" width="100px;" alt=""/><br /><sub><b>Luis Blázquez Miñambres</b></sub></a></td>
    <td align="center"><a href="https://github.com/Alburrito"><img src="https://avatars.githubusercontent.com/u/25366155?v=4" width="100px;" alt=""/><br /><sub><b>Alvaro Martín Lopez</b></sub></a></td>
  </tr>
