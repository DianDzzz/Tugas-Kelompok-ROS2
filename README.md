Kelompok 4

---

> How to Run?

source /opt/ros/jazzy/setup.bash

colcon build --packages-select sequential_turtlesim

source install/setup.bash

ros2 launch sequential_turtlesim relay.launch.py

---

Anggota:
- Arvito Rajapandya Natlysandro | 5054241046
- Fazle Mawla Wahyuhanda | 5054241020
- Umar Al Faris | 5054241015
- Muhammad Hadidan Nurhaunan | 5054241016
- Marvel Mahanara | 5054241047
- Tri Ismunhadi Julik Cakra Wibawa | 5054241017
- Muhammad Fathur Aziz | 5054241043
- Mohammad Akmal Fayyazi | 5054241045

---

Urutan menggambar di turtlesim:
- Arvito --> angka 1 dan 9 | warna pink (sekaligus lakukan /clear di canvas turtle sim setelah siklus selesai)
- Fazle --> angka 2 dan 10 | warna biru tua
- Umar --> angka 3 dan 11 | warna oranye
- Didan --> angka 4 dan 12 | warna ungu
- Marvel --> angka 5 dan 13 | warna hijau
- Awi --> angka 6 dan 14 | warna kuning
- Fathur --> angka 7 dan 15 | warna merah
- Fayyazi --> angka 8 dan 16 | warna biru muda (sekaligus lakukan smooth transition ke idle mode setelah semua sequence selesai)

> state awal turtle sim, kosong

| x | x | x |
|---|---|---|
| x | x | x |
| x | x | x |

> setelah siklus pertama selesai

| 1 | 2 | 3 |
|---|---|---|
| 4 | 5 | 6 |
| 7 | 8 |   |

> setelah siklus pertama selesai, di clear

| x | x | x |
|---|---|---|
| x | x | x |
| x | x | x |

> setelah siklus kedua selesai

| 9 | 10| 11|
|---|---|---|
| 12| 13| 14|
| 15| 16|   |

