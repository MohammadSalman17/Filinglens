import base64
import io
import json
import os
import os
import re
import time
import uuid
from pathlib import Path
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from guardrails import MAX_QUESTION_CHARS, MESSAGES, check_question

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/ask_stream")

# Local: chats are saved as files. Public deploy (PERSIST_CHATS=0): chats live only in
# the visitor's own browser session, so nobody sees anybody else's chats.
PERSIST_CHATS = os.getenv("PERSIST_CHATS", "1") == "1"

APP_NAME = "FilingLens"
TAGLINE = (
    "Ask questions about annual reports of Apple, Microsoft, Alphabet, Amazon and Tesla. "
    "Every answer comes with sources."
)
ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAd1ElEQVR42t2deZQkV3Xmf/e9yL2quqt6l2w1jTYjFgskQBtILdAg"
    "C4ZtqB6wZcQyx4yxMBwwePDxTNO2MWe8AoczM4czeBnAg7vGMHgEkkeYRowQSGhHG6AVobW7equs3CLeu/NHRG6RkVlLVrckR5/o"
    "zMrMFxl5333f/e69790nLPPYvVsNwJ494gEu/4hWooBXqmvtRORsxZ+O6kYVLYlIoCgIgKKSXEQUAE0e6TyC0n1Nk9dIrtG9Vvd1"
    "zWo/pE3n+zLvYfAe09fuvK8+UqEOckAsP0a5WXL5fdEEN177zm2LWXJa6pClP6IyO4uZmxMHsOtjrXOsyuWKXoqYk21gUcB7j2qE"
    "qmdQ+BnCSAurLciOsNrv9QqjLbzk/bbAOr9iRGcPEe5gx/Xcb0oxEAERxBgkyIEIPmqg6AMicg0Sfema9+/4AcDsXrVzu8R3b3QV"
    "HbB7t5p2T+76qL4swH0CMf86yAthCM41QHCqKnT/9QhniCYO6Zz0a2nNTwurMxaW0vzMUdPbmSM6J9UmaaUqqgoqgjW5ArZQImou"
    "IsI/atjY808fOPXWtAxX1AGzs2rn5sSdMXtX/pe3v+ATInzE5Ew+bDZVUQcYjBh6tX3IkF5a81cOO/2dt8aws4zRkhp1XlCvqA3K"
    "U+LCRgv8n8/femD3LZ8/O0xGg1t2B7Qb/Nvfapxmy8HfBHl7brPRAvUOIzYtrGzhrwB2smAgranLEcZawE6GjRo6crPuBXWI2NzE"
    "NFGzeoPWqu/61ode+NNhnWDSL1y4e18wt0vcrg+1zrel4HoT2HMbtWYEqlnC1/YNiQ5o5LCb1x6Mzdbi3h9Hz/XbAh38nkxhSRbs"
    "pGGtje8pG9R331mjprd99zURsaAaVucjm8ufZyqV6y/67I/On9sl7sLd+4KRI6ANO7s+VDs/yOX/L2LLLmo4xNgsmHh2wM5wzT+W"
    "sLOc36zqI5MvBoqvRbXqv/rOb7/4e7N799q5XbvcwAjYvVvN3Jy42Q82TrdB/usgZRc1Vyh8XabwyRA+KW0eT/iaFkbqHnuArdM+"
    "fb1MNpce+T3XS38fRgIX1p0I5aBc+frO/3Lv6XO7drk2Ve35yTHVLJ9BrrkQfT/IB2eGreGa3wcBx5rtZIyWpUba+GxnCRszihpn"
    "2BjvvctVJm3UrN7ugsK5mys/DOdmZz0icU+0eX79aOuThVJwZqvVDEdpfr+X0K+9WZrfbaMpzcmGHXq0U1OjZaTBJRu/R8LOcoXf"
    "e1+ZRnqIcgJijY0aC2Gusv5ME9b/aG7XLjc7F6OPxLiPf/uHW2caa37oVVH1Bkku/wyynTTsDP2+JTxYSTlWyvhsZ/D++3/r4P2q"
    "IsZLEGgU1l9+3W+88I7ZvXPGtO/AK5+0ucCqOrKEf6zZTodFmCzGkmIfyftC4pwaTdqCETDJoyS/zim0nNKMPJHXbpsx2E76Mf1b"
    "B2BXEK8Oky8EAp+kV8Rv/3DzpWLtzd47NIGl4812xEAzih3GfE56NLWtxf10UURjwUYeYwRjlMgrThWvcVtjIBdAKW+YLBrygVBt"
    "OfZXI7wq5YLgdQ3Yzkib2D9aFLzJ5YjC1tnf/XcvvC1Ihvp78wVrGvUwAjFrCztLsR3wCq2W58QNFhV4bD4inxMC2+EdeBSv4Jzi"
    "UEIXC/CkTQGLTU+tBZsrlumyZcOEZeNkwMYJy0zFsr5smShYBIi857GjLa6+e4GbfrbIRNHgVceHHRgBm712R70tlgMXtt4LXClv"
    "/KhOllzzLpPLneSilmJEjiXbkQSTpUPfFIdw5RsnefWL8qBw3d1NPv2PR2m2IiTR7nwglArCZMmwvmzYNJ3jjS8vcfoJeWpNz/7D"
    "imsKpTxYE4ekVGP4cV6JHJTKhs0zEFjwHv7bdw7z9zcfZKoo8agRwUvXaC+f7QyDnQwqrV5NviAuaj7CBC8KSto41wT5k5xrKQYZ"
    "xXZYEdvpYnLXMVG8Vxo2T0sCjIUjdeWd5xtee2YBTQKOl5xZ5HDTcucTlu0bDTMTMF2BdWWoFCBvYfu6GGIAJkuGyRI8egiqruc2"
    "2tCFYIHN62PhOx+3ff/F63mkHnDt/VXKOUA9Jd8iwOG7jZcNO6P9lOR1I+LCpppcbju11nmBwMUmMLgWHrDjw078t5HY8EUuxmVB"
    "kXxArpTj9NajvDh8mEqjRnOhzoVbLsC7X+jpKHjbift5w0M3Yw4U8E97nI+11vkEil5/IVRKGCNo0nMzP/kR5R8/hCnk49dIrHQU"
    "YafXEVz2alDFCqgHjPBbzZt4wVOPYStFHsnPcFP5ecxLkUnf6MhgXNgZoMqCN7m8DevN1wZO5SyTNBORJXp2adgRA2GkhB62TAsn"
    "bMixcVKY2RCwOahz2g1f4eSnbwFtxr1UXYD7PLz08v74yL5/pvSNq2BiIpZ8h5EYqNfg1M1w9tngPZIMhco1/0Dl/vuhWOxpI/Hz"
    "fB7OfTFMT3fbHDzISdd+hXdpBIcNiOGp4kb+eutOvjH5S5RdE0WG+AhD2c4QB7BHsVFRdYiRM+2Lzv+9PYidVnWIdEbsymFHYibT"
    "aCkb1xl+dWeZt5xX4rwX5HnxKTlOn6pz5tc/zcwjd4DN4ySPSg7NVZCfPYpMr4etW2Nh3XgjXHMNOjEJuUIsvHyh75SHHoKTTooF"
    "WqvB178Od9yJTq2DINf9bC4PxRKEDvn5z+Hkk+MOOnAAvvhFdP88vjCBEoAETIZVLjj8I2y+xPcrz6OoIRobrtXDTpruSgxF6p3I"
    "7EdrR4yxU15dTMhWyXbEKM1QOWGj5co3Vti0zlBrgPeKKwgn7P0CE7d8F103jXFRKummEIawZUv891NPQS7OOGVnMST+vDGweTPU"
    "6zA/D6VSfK1hbZpNKJdhZgYOHow7rlDoa+PFoN5jxfHbp13BrYVtVHwLl+knrDQk3vGkFWNF1R0xCCVVH4t+tU6WKM5DPgdXXFJm"
    "ZtJwZDE2uuSF8pNPMnnfrcjE1KDw28IpFGD//vgsFIYLv91huVzcAU88AUePxoJVHd2mWIw77rHH4sdicaCN0cRCu5C3HbgVb0xf"
    "inLFsJMZzkFUPaBlI0hO+6KCK4/tiIFG6HnZKXl2bLEsNmK2Iar4AEo/vx+addQsQ6i53GhB9n4eYngKgi7mjzq8jzs2n+/ahozD"
    "qILkeEH9caZ9nVAkps0DyqnZVDMVz2J4SCVnshPoKw0px48vOCnoUMlei2qqC8sX6nI+txZtlpyuIJTCBnnX6iiOZnjMmhWU6wuJ"
    "Z4RzetoEWYZkuU5W5z2NNX6ybGLXfjU/+Fl1aOe+e3jLkDjQCLYzRLa9IfMgK0SwHCer7z0Bp7ERFuFf3BF7sCyP7YyEnUHvOBg3"
    "ttO+qPMwv+Bjz1eXN+PoOTEOOsRkMLGzNNtJBx5TLpzQHQErhZ3ei0ti7Q8cddlzLUTA2m7s4DlxSPd+00q1GtgZkgwKVgs7/R5h"
    "7KDOVx3OZ6T9Wy04ciSOjHn/HFF/D7mokwfWNYSd3tcCMrJIKw0pt2Pvh6qeVtQbgBNoAmecAVO/FnumzxWDrApq0adyqPfJ9IU1"
    "gJ1Um2C1sNPXOYA1cLTuqDWVSlFwHkQEWsAZp8JZpz43DcEX74d62NG4sWAnYwJAsGrY6fmsohgDi01loe6ZKlmcdtN5tBTynucU"
    "RVKFlgd8drJmNbDDYCozGIjqrSCT1fsFJvGGD1U9J220KWufGOHn2mF6/H2RodNklgM7OiSxE3TyrCuFnXSkTyDyynzVYUzuXw4V"
    "ldH58ZXBDgOjJuiNUq8Ednrn7fRe+8BClE1Fn9PeQDu+Mi7sDMo0UFk97GjKGxYDB6ruOcM0l+sO0JcjHh92etsEfUkCVgg7KTZg"
    "DBysug4VXQnhdM6jx1GmqkoQ2KU/2B4DKfmMAzu9nRP0afYKYSc9BGMq6qm3lFJesgNzqcEtwKOPz/P0/qOIkePjJ0g7+m05dcdW"
    "SsX8iHtshyFkzWCnd2QEY8FOD3tSwFioNj1H656JosW5pRXMe8+TTx8hjKJ4wc3xGgVGWKw1OXR4kdLWOIkvWTR5QBbjwU7fSEqH"
    "o1cMO6nQrBFoRJ5DNccvbrAQLT0CjDFs27KeJ58+gjnOI6C8rsLMdCVhyjL8LgdGwHiw09smGBd2+iYuSTxtZL7qlmUD2pf4hW0z"
    "bNu8/tlnA/pC9D2/ZxzY6c0+9gbjVgM7aW2Q5EsPVKMV01Brn52RUiVjWew4sJM2wuPCzsDihh4qKiyfCekxgB5Zi9CH9PsB48JO"
    "35q0wRGwCtjp51BYAwcXI0LX77scF2Edh9GwLNhBUTGgLjF06Q7tNcLpYbVC2OmnsbEvcLjuqLeUYl4G8wMZR73R4uChxfhaOj7A"
    "q0KxkGPDzOSaOOSaOR0xA3ZUUSuYXA5p1KBYiKl42EKNGVj9GRvhdC5gNbDT7hCJR0C16VhoOCqFgNYSAvWq/OTBJ6kuNuKJ2WsE"
    "PZHznH6ysmnD1HCKuQoIGgU7agxWI/w1V9N4+GfkN20g2HkR0aat0KjFoYKUbE0/gCy9JqsveDfgJcbf0YiUQ3XPcuyqHKOwUXv1"
    "zNrADoNYmgE7Nm/x37qahZtuI6zWqd73IPUvf4XgoZ9ApUw8GasfXQIdF3ZSPSoCoVfmqxFG8ktTURFOO3kr8wfXHoI2zkyOb186"
    "MpCBkd+Wj6gnKpbJ3fhtjtx6FzI1FU8ALpdo1UPc33+Nyut24s8+G9dsdtesdcLRK4KdDIOSStCrKvur0bKNcLGQ58Rt+bU0lQm+"
    "uWTYy1jX6/cB+h8tjqN2gp31m7n7luuJCmXy3sX+pCoSWJwaqld9i8rhw9idF+Kc6yi2GRYJ7e/pwUlF2Un8RCMMHKhGnfVXy6Wh"
    "qz+T9vG3d06MXaMsnJLOmyhKII7DlDkn/1M+XpjjcKsQLw7s/2HxLMhSieq+H8B3/x+S706/DFaz/J8ReeR2VHS+FlNRswLDuXr5"
    "JEZy/hG479tdCSjwSxfDhu0MzplcaUKm/7caURY1z3Y7zx/kv8ymoMm7z23wn68ts64Uh2V8n/+laKlEeO/95M5/JZGxCL53XtA4"
    "tRf62YHtoaKBOdb8Prl/F8LXPg4/uw1yxfitsA73fgve/TdgA1aXphv0gEWUEEPRtPjTyhfZxEGiepF//6ojbMyH7L52CkQo2ngl"
    "Z9IIwhCzaQZfyEOzBUYwq629kLYTvct5TJuKNh12Je7wODQlrEPtEExuhsp0fE5ugdrB+D1kdfchPXUkUCSRQZMcf1ie43R5CBeV"
    "CJzDVYW3vazKF948z/q8ZyE05IxijaBhRH79BMFrXoVP1iprTEPHhZ1B99wK1CPP4brDGo5TkE1ALPgoNr7exc/Fjkl0tY8vGzyH"
    "KfHh0je5KLgZF5axLgKnWK9ER4VzTqrxd29+kjNmmjxVDzjUEAKjFN56KeHGjRCGqKE9L2gIxKwEdtK+goEw8swvRpjNhTXpgPY6"
    "4d7DSNrG6GhWtEovuEsZHfM6wTuKN3B5/tpY+N4la2HjWX+BKm7RsH0q5Mu/8iRfumeSo0cibjznLTy842SCxmLsFSf3ZVgD2On9"
    "WzseLuxfjNZsKpBBCKT/NMcp868oNmE8r8rfx8eKX8VHeYzz8ZrXdgc44pGgHt+AsoH3nfEoz3v92TxwytnkGovxWoPejNg4bGdU"
    "1RER2L8Yjp1faZvNB+tVrjnwRN97l27cxvNLE8d4BoxixbOoBXbYp/nj0t8ROI86i7ge7e89I0XVYBpHubpyAbsn3sRkqy38VDg6"
    "K6azGthJe9TGwHwSFS3LWOhLy3s+cO/N3HhknrKJkyg157h6/2N89cxXExhzzDpBRGlhqZgmf1b+Euv1CD4qYDKFH48G7w22VeXu"
    "4ql8Yts7mKAZG92MidBBX5RvVNHSEbCT5RVbA4fqEfVImR4DhwSoe8d8q8nWfJEgudZUoOxvNan5iHUmf0wMfTv4EGL54/KXOVke"
    "6TO6OCDq7wTvBBPWecps4MNb30MoloK28CKZATyDrJLtkBU91U6VE2NhoeWotqnomIE1K0Kk8ap7p0qkiu0sbD5GvEo9RyjxsdJV"
    "nGduTwlfU/jvUSfgQhqa46Pb3svj+WlK2uwIXzOKfwRLa/7yYCcdzjB9VDRY0pH1nj4P1ph+TFl7frM071q0ea4oXs+v6j5cVOln"
    "PAMneOexYciere/hh6WTmfELRMlMj2GQbpYTjBvKdkbU4hSB0HkO1CKWcobbc3etSU77zE6klqQu7YbDd/A+/V+oL2KdS2l8m3rG"
    "j5EXbKvKf93wRr627pV9wh+adUyHo1fDdoYV1BMBh3JgMUyEOWgm2+GZx56EG2/r/4pzzoITtjwTeUcfO2+1x7G3/hFEGv/UAeH7"
    "DuNxzhA0j3DV1Kv43IZLmXa9mp8Va+uZG7qWsKPpYnUCT3eoqGRGEKII/vLzcM9PoZBEpJtNuOEW+NTH44pXx21NTVsjokW4eQ/U"
    "DwHl+CYTYXepZsz5nTfYcIHbSmfwiS1vp9KuspIVMWZQpsG4bGewzFdPTEhgvhYS+RSp7+Y4aLTgSBVm1sdrjQGiMhxdiN/LBRyn"
    "HtDuDd7+J3DwJ2AmIYw6MNMPPR7vBBvWedxu4Xe2vQsP5PCx0R1ZW6IbuDTjsJ2RNdYSKnqwEdGIdDTDMdCBWB8/N+Y4z3BXHydv"
    "7vk8/Pw7YKdi4Q+wnS7jkSikpgU+vO297A+mKCZ0UzMrvWevvzDZdTx787+6TNhJdYjEpcOOtiIWmn4ka8nylo/rWj51Me4/chX8"
    "9H+CXRcX8/A6CD0urh3vnUeiiP+45de5o7SdSV8jEtNXQzQLdtLyNozBdrJgR3u+yBioh57DjYhn7dEW/v5b4EefBTMBkRsCO4mz"
    "5QXbWuTTG9/CN6ZexoyrEontMrfeWhIyfK+DJBi3drCTprQicRhhvh520o7PLuEnjKf6KNz6SfA2Caj5lNbTZTxesM2jfHXdRXx+"
    "w2s7jGdJ2JHBxJfKME94tbCTkUd2quyvhc9CzU9YQLgQM57GAmgu1v4hMZ5Y+FVuKr+EP9w8y6SvownmLwk7ZFN701OnfGzYGVjC"
    "n1yttcT0uGRrloEzHRHNOnXYhci4UJrxqMKtn4LDD4CUErpJpqfbZjyPBCfy0W3vxIjHtBlPuoTNErDTH45OW+dlOFksewOFuDNG"
    "ebXGxGQj7K6FJgzj19qlGgIRWuppqUeSFEb773ZwDmMgasVn+4haEIVxYGpA+w3c9Tl4/HsQrI+/NJPxKOoFiVosaJmPnPAeDtkK"
    "E9pInK0lYGeI5ndGQO/OEWsCOz2jRpfQelUoFeF1F8LkJExNxOfkZPxauRivN5gIAi7ftoPpXJ6ZXIGZXIHpXJ7Lt+2gYnN475F8"
    "Bc56G5TWQzk5S+vhrH8D+XKC99Klm4/+E9w/B8G6HuEPnuoUHzk08vzetiu4p3gik1ofFP4KYKcXOeRX/vxRXenOEcutKNsOSV95"
    "/mbeedYGnI8T1FlHvdGt42FM3DHpo+rims9xOlKYsBlBvuZiUhSUWNCFSjbfv+F34KnbY+gJez3dxABHbaMLtlnlTza/g7+avpgN"
    "/iihWEZWdR9ZACu1UHtw2cx4sNNf2lGS9KQuaQ/TAk9P41F0QOCK0heQVs0QePpCnsbB+ynYCSRsQVAayGa1n7cZz1fWX8JfT1/U"
    "E2AbD3b6/YA1hp2Bku4GDtZHL95uw1HvmbYbPWXzeoIGMnghei5C74WSQuFRnfDAPdTWvRg/eQrUF8DLoNH1Btta4HuVl/KpzW9l"
    "ytdxIgOTdVcCO33CT/43ioaIDNkzZZlsZ8iiZQXyVvjRU/VsgY1gQsPCFr3n8OkpPUwoxS9cfR58hAYlaqe8lWjjL0NjMWY/vit8"
    "aS7yQH47v7vt18kRIfgB5VwJ29F0sNKAoqFBqNOXLluekzV8247uEPQopZxw3/46331oASMQumfWGXOL+5OSlRGop37KZbSedxE0"
    "GxBGeLVofREpzbBn+29w2BTIa9QTYFu+k5WVZ0lklxTX03oAfl5sbkqjSAHRjNK8K4GdrGGZs8JfXP8Ez58p8Ivr4pizU12bKOdy"
    "J/8Cxke4xiGkM1nLI1GD5o4L0Pw6gruuxS4egsoGPvP83+Tm1gbW+8UY90fADiuBnfZzaxB184EKD4i1O9SllpEMW7S9BOykNcQD"
    "+UCYr0d84KqH+dB5W7lg+2Q8Z/R4Z72aC7jWIsb0zBMV0Fad+tYXsn7T8znSzPEXh2b4hyM5prTWJ/zlsJ1hZCbVESo5Kz5q3R8I"
    "3CLGvLar9qthO2nIok8bvEIhJ8zXQ/7DtT/j1A1FXri5xOaJXE95M0XT3m3q+u0NeToVzXUQ5iW1ZoukTd0bdk7t57QAqpESmNje"
    "ikDFgmide6Iinzm8iX0HIzaYBq5X81fBdoYV+lbiSKXCbYEX/baLmr/bDcyNDzv9vZ/MBtAYivKB8MChBvfO1zpbh+jIFejpVTnZ"
    "3Hqg5EKPgIwVFhsRdz74ff7yHadSLudo1EOmcvHs5ZurefYeLPHdo3lavsHGQIg4BrDTtZPGt1oo7tqgZWs3FCJ9xOSL213U9DAY"
    "oFsp7AyrLqhJRLSYE0piu9cYcPSyHJk+I9Zvo0ZNEEAhFzDdWGTfN+/i3Q88wZ9d+XK2bJ5k3+E8cwdL/KCaJ1SoWKUcSFxhYa1h"
    "p3uv3hTyxrVaD7tg4QfmuitfVBVj/o8tlGMvZRVsJ3NzTAZrKbd/kO/M7/HxXB/ffd6Z+5PsiBR5JVKP8z6ZD+Q7c4OcT9qTvEbv"
    "+8n1vCeyhuZjTzAR1rjlrid535cf5P0PTvPBh9dz/UKeglGmgnhluUuNpHHYTlZhJ0W9KRVB9Kp7du6qBgCRD/+KVvX9caQru5Dr"
    "amAHGOoBLmsb8YEE0fDaC32rldMEAsU+vR//kjPY8qpX8PTmTfx8QZkIfDIDqF1XRI8Z7HRmixgxUb3mxfAFADO7d6/95w+edpsP"
    "G1cHpUmjqm55TtawEu7ZBQBXInxdonTawLbnwpAtazWeGdBsIuecRfD2N+FO3EoOT8V6kpqImQn0cZwsHVYQHe/sRNn4VvObd+x8"
    "3e2ze/daA7NxEwl+30eNSKxN6qGvHewsXWONIZm4pYWfbjPY2fHfUbmENpvQasVrDXqY1WoyWSuDnTgoJdbiWs3Ii/x++5Nmbpe4"
    "2b2Ya6/ccXsY1j+bq6yzQJQJO3KsYEczdptgac0fgMksASTpUe9QI539YNL2bU1iO0N3YQVFIzs1YX2r+Zm7X3PpHbN795q5XbuS"
    "nVFUZXZuzjy9+PJcUHffD0rlM8PaUSc2yWSskO0wRKt02cWOlqf5OjIk3s/Vs7Yd0TFCykuxnb7tC1WdnShbX6vfdlhy571i//7+"
    "7WwR0TPuntXr3r2jIcIuH7UO2ELRqnr3bIWdtDB0CUcprbXHBXYS4ZtC3vqwdUBd+PZHdu5szM3Odlb7dZZY7dkjfnav2m/95ik/"
    "DesLb0ao2XzBevWub63sMww7SzlgvbAzcpuR4wE7ifAVrUWL9TfdecnrfzK7d69FxA8NZc3uVTu3S9yFn7vrgly58jUT5DZG9aMR"
    "Ira7ze0zAzs6yul5NsEOqqre2clK4MPwgDYab7nzksuun1W1cyJ9pQwHFrLP7RJ34e59wXVXvuj6Vr36ahe1bs5NzgTxfrjqnlG2"
    "I6OrUz0bYEfxDoME0+sDH4Y/jOq1V995yWXXX7hvX5AWPkBm1bpHrvtbP7tX7dXv3vK0vfh1/2PSTFqsfUVQquRc2FAEF1NXkVU5"
    "WWPCDoyuy7bkfseM5vkrdrLiKWdOBLGTE0ZVmxo2/3Txtruu+PGvvfPJ2b177Tff8Aa34mj67t1q9uyJ8erCz991pikU/pOovsWW"
    "KrhmDRc2ARyi0s4k0H12TGDnGWc7XR9JVVBQK/k8plTE12sA/5uo9YnbX3PpHXGD3QbZ48dIZ6jM7o39BYCLvvDjVxJwhai/FCM7"
    "TK6Aqkc1Qn2EV5+EgTWzAODwwNlSmj9EgCM6bKnFESMXo2TZOZNsE2sNEtg43xGGoP4hNXKNuvBv77z4dTcCzOpeOye7PEuknZad"
    "Etm9Ww2fgD2JBT/vv987mcuZVwr+YlX3Eq/u+WLMRtStw5i8Zmz2ObwSV8970hv/X6bBzax5t8RIWxJ2MpRFfUuNHAE9ICIPquFO"
    "ydlv5xfqN9102WVHE/vbpvbLKmH+/wE5kkfXigfosAAAAABJRU5ErkJggg=="
)
ICON_IMAGE = Image.open(io.BytesIO(base64.b64decode(ICON_B64)))

EXAMPLES = [
    "What was Alphabet's total revenue in 2025?",
    "What are Tesla's main risk factors?",
    "How did AWS perform in 2024?",
    "What did Microsoft say about OpenAI?",
]

st.set_page_config(page_title=APP_NAME, page_icon=ICON_IMAGE, layout="centered")

st.markdown(
    """
    <style>
    #MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"] {visibility: hidden;}
    header {background: transparent;}
    .block-container {max-width: 760px; padding-top: 4rem;}
    .hero {display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.3rem;}
    .hero img {width: 52px; height: 52px; border-radius: 12px; animation: floaty 4s ease-in-out infinite;}
    .hero-title {
        font-size: 2.2rem; font-weight: 700; line-height: 1.1;
        background: linear-gradient(90deg, #5B6CFF, #2BC4B4, #FF8A3D, #5B6CFF);
        background-size: 300% 100%;
        -webkit-background-clip: text; background-clip: text; color: transparent;
        animation: flow 9s linear infinite;
    }
    .hero-sub {color: #8a8f98; margin-bottom: 1.5rem;}
    .stButton > button {
        border-radius: 999px;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        border-color: #5B6CFF;
        box-shadow: 0 8px 22px rgba(91, 108, 255, 0.22);
    }

    /* soft moving colour glow behind the page */
    [data-testid="stAppViewContainer"]::before {
        content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
        background:
            radial-gradient(620px circle at 18% 8%, rgba(91, 108, 255, 0.10), transparent 60%),
            radial-gradient(520px circle at 88% 30%, rgba(43, 196, 180, 0.09), transparent 60%);
        animation: drift 20s ease-in-out infinite alternate;
    }

    /* new messages slide in */
    [data-testid="stChatMessage"] {animation: fadeUp 0.45s ease both;}

    /* example cards: staggered entrance */
    .st-key-ex_0, .st-key-ex_1, .st-key-ex_2, .st-key-ex_3 {animation: fadeUp 0.5s ease both;}
    .st-key-ex_1 {animation-delay: 0.08s;}
    .st-key-ex_2 {animation-delay: 0.16s;}
    .st-key-ex_3 {animation-delay: 0.24s;}

    /* source chips pop in one by one */
    [class*="st-key-src_"] [data-testid="stColumn"] {animation: popIn 0.4s cubic-bezier(0.2, 0.9, 0.3, 1.3) both;}
    [class*="st-key-src_"] [data-testid="stColumn"]:nth-child(2) {animation-delay: 0.06s;}
    [class*="st-key-src_"] [data-testid="stColumn"]:nth-child(3) {animation-delay: 0.12s;}
    [class*="st-key-src_"] [data-testid="stColumn"]:nth-child(4) {animation-delay: 0.18s;}
    [class*="st-key-src_"] [data-testid="stColumn"]:nth-child(5) {animation-delay: 0.24s;}

    [class*="st-key-src_"] button {font-size: 0.82rem; padding-left: 0.5rem; padding-right: 0.5rem;}

    /* question box glows when you type */
    [data-testid="stChatInput"] {transition: box-shadow 0.25s ease;}
    [data-testid="stChatInput"]:focus-within {
        box-shadow: 0 0 0 2px rgba(91, 108, 255, 0.45), 0 10px 32px rgba(91, 108, 255, 0.18);
    }

    /* pencil (edit) button: only visible when the mouse is over the question */
    [class*="st-key-editbtn_"] {opacity: 0; transition: opacity 0.2s ease; margin-top: -0.4rem;}
    [data-testid="stChatMessage"]:hover [class*="st-key-editbtn_"] {opacity: 1;}
    @media (hover: none) {[class*="st-key-editbtn_"] {opacity: 0.7;}}

    @keyframes flow {0% {background-position: 0% 0;} 100% {background-position: 300% 0;}}
    @keyframes floaty {0%, 100% {transform: translateY(0);} 50% {transform: translateY(-4px);}}
    @keyframes fadeUp {from {opacity: 0; transform: translateY(10px);} to {opacity: 1; transform: none;}}
    @keyframes popIn {from {opacity: 0; transform: scale(0.8);} to {opacity: 1; transform: none;}}
    @keyframes drift {from {transform: translate(0, 0);} to {transform: translate(-30px, 20px);}}
    @media (prefers-reduced-motion: reduce) {* {animation: none !important; transition: none !important;}}
    [data-testid="stElementContainer"]:has(iframe[height="0"]), [data-testid="stElementContainer"]:has(iframe[height="1"]) {display: none;}

    /* Thinking indicator: bouncing dots + shimmering text */
    .think {display: flex; align-items: center; gap: 0.7rem; padding: 0.5rem 0;}
    .dots span {
        display: inline-block; width: 7px; height: 7px; margin-right: 4px;
        border-radius: 50%; background: #e8825b;
        animation: pulse 1.2s infinite ease-in-out;
    }
    .dots span:nth-child(2) {animation-delay: 0.15s;}
    .dots span:nth-child(3) {animation-delay: 0.3s;}
    @keyframes pulse {
        0%, 80%, 100% {opacity: 0.25; transform: scale(0.8);}
        40% {opacity: 1; transform: scale(1.15);}
    }
    .shimmer {
        background: linear-gradient(90deg, #6b7078 0%, #f0f0f0 50%, #6b7078 100%);
        background-size: 200% 100%;
        -webkit-background-clip: text; background-clip: text;
        color: transparent; animation: shine 2s linear infinite;
    }
    @keyframes shine {0% {background-position: 200% 0;} 100% {background-position: -200% 0;}}
    </style>
    """,
    unsafe_allow_html=True,
)


TAB_JS = """
<script>
(function () {
  const P = window.parent, D = P.document;
  const ICON = "data:image/png;base64,__ICON__";
  const NAME = "__NAME__";
  const ACTIVE = __ACTIVE__;

  function setIcon(href) {
    let links = D.querySelectorAll("link[rel*='icon']");
    if (!links.length) {
      const l = D.createElement("link"); l.rel = "icon"; D.head.appendChild(l);
      links = [l];
    }
    links.forEach(l => { l.type = "image/png"; l.href = href; });
  }

  if (P.__flTimer) { P.clearInterval(P.__flTimer); P.__flTimer = null; }

  if (!ACTIVE) { setIcon(ICON); D.title = NAME; return; }

  const img = new Image(); img.src = ICON;
  const c = D.createElement("canvas"); c.width = 64; c.height = 64;
  const x = c.getContext("2d");
  const colors = ["#FF8A3D", "#5B6CFF", "#2BC4B4"];
  let t = 0;
  P.__flTimer = P.setInterval(function () {
    t += 1;
    x.clearRect(0, 0, 64, 64);
    const s = 0.68 + 0.04 * Math.sin(t / 3);
    x.drawImage(img, 32 - 32 * s, 32 - 32 * s, 64 * s, 64 * s);
    for (let i = 0; i < 3; i++) {
      const a = t / 4 + i * 2.094;
      x.beginPath();
      x.arc(32 + 27 * Math.cos(a), 32 + 27 * Math.sin(a), 5, 0, 6.2832);
      x.fillStyle = colors[i]; x.fill();
    }
    setIcon(c.toDataURL("image/png"));
    if (t % 4 === 0) { D.title = NAME + " · Thinking" + ".".repeat((t / 4) % 4); }
    if (t > 1000) { P.clearInterval(P.__flTimer); setIcon(ICON); D.title = NAME; }
  }, 120);
})();
</script>
"""


def tab_animation(active):
    # Animates the browser tab icon + title while the answer is being prepared
    js = (
        TAB_JS.replace("__ICON__", ICON_B64)
        .replace("__NAME__", APP_NAME)
        .replace("__ACTIVE__", "true" if active else "false")
    )
    if hasattr(st, "iframe"):
        st.iframe(js, height=1)  # newer Streamlit
    else:
        components.html(js, height=0)  # older Streamlit


def thinking_html(label):
    return (
        '<div class="think"><div class="dots"><span></span><span></span><span></span></div>'
        f'<div class="shimmer">{label}</div></div>'
    )


def clean(text):
    # "[Source 2, Source 4]" -> "[2, 4]" and escape $ so it is not shown as math
    def citation(m):
        return "[" + ", ".join(re.findall(r"\d+", m.group(0))) + "]"

    text = re.sub(r"\[\s*Source \d+(?:\s*,\s*Source \d+)*\s*\]", citation, text)
    return text.replace("$", "\\$")


class UserFacingError(Exception):
    """An error whose text is safe and useful to show to the user."""


def stream_events(question):
    with requests.post(API_URL, json={"question": question}, stream=True, timeout=180) as r:
        if r.status_code in (400, 429):
            detail = r.json().get("detail")
            raise UserFacingError(detail if isinstance(detail, str) else MESSAGES["injection"])
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                yield json.loads(line)


def render_sources(sources, key):
    st.caption("Sources")
    with st.container(key=f"src_{key}"):
        cols = st.columns(len(sources) + 1 if len(sources) < 5 else 5)
        for i, s in enumerate(sources, 1):
            year = f" FY{s['year']}" if s.get("year") else ""
            with cols[(i - 1) % len(cols)]:
                short = f" ’{s['year'] % 100:02d}" if s.get("year") else ""
                with st.popover(f"{i} · {s['ticker']}{short}", use_container_width=True):
                    st.markdown(f"**{s['ticker']}{year}** · chunk {s['chunk']}")
                    st.caption(f"Report {s['report']}")
                    st.write(s["text"])


def session_allowed(max_calls=8, per_seconds=60):
    """At most 8 questions per minute in one browser session."""
    now = time.time()
    times = [t for t in st.session_state.get("ask_times", []) if now - t < per_seconds]
    if len(times) >= max_calls:
        return False
    times.append(now)
    st.session_state.ask_times = times
    return True


def start_edit(i):
    st.session_state.editing = i


def cancel_edit():
    st.session_state.editing = None


def save_edit(i):
    new_text = st.session_state.get(f"edit_text_{i}", "").strip()
    st.session_state.editing = None
    if new_text:
        st.session_state.messages = st.session_state.messages[:i]  # drop this question and everything after it
        st.session_state.pending = new_text


def set_pending(q):
    st.session_state.pending = q


CHAT_DIR = Path(__file__).parent.parent / "data" / "chats"
if PERSIST_CHATS:
    CHAT_DIR.mkdir(parents=True, exist_ok=True)


def save_chat(chat_id, messages):
    first_question = next((m["content"] for m in messages if m["role"] == "user"), "New chat")
    title = first_question if len(first_question) <= 38 else first_question[:38] + "…"
    data = {"id": chat_id, "title": title, "updated": time.time(), "messages": messages}
    if PERSIST_CHATS:
        (CHAT_DIR / f"{chat_id}.json").write_text(json.dumps(data), encoding="utf-8")
    else:
        st.session_state.setdefault("_chats", {})[chat_id] = data


def load_all_chats():
    if not PERSIST_CHATS:
        return list(st.session_state.get("_chats", {}).values())
    chats = []
    for f in CHAT_DIR.glob("*.json"):
        try:
            chats.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue  # skip unreadable files
    return chats


def list_chats(limit=30):
    chats = sorted(load_all_chats(), key=lambda d: d["updated"], reverse=True)
    return [(d["id"], d["title"]) for d in chats[:limit]]


def new_chat():
    st.session_state.messages = []
    st.session_state.chat_id = uuid.uuid4().hex[:10]


def open_chat(chat_id):
    d = next(c for c in load_all_chats() if c["id"] == chat_id)
    st.session_state.messages = d["messages"]
    st.session_state.chat_id = chat_id


def delete_chat(chat_id):
    if PERSIST_CHATS:
        (CHAT_DIR / f"{chat_id}.json").unlink(missing_ok=True)
    else:
        st.session_state.get("_chats", {}).pop(chat_id, None)
    if st.session_state.chat_id == chat_id:
        new_chat()


if "messages" not in st.session_state:
    new_chat()
if "editing" not in st.session_state:
    st.session_state.editing = None

# ---- Input (question typed OR example clicked) ----
prompt = st.chat_input("Ask about Apple, Microsoft, Alphabet, Amazon or Tesla 10-K reports", max_chars=MAX_QUESTION_CHARS)
pending = st.session_state.pop("pending", None)
prompt = prompt or pending

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

# ---- Header ----
st.markdown(
    f'<div class="hero"><img src="data:image/png;base64,{ICON_B64}">'
    f'<div class="hero-title">{APP_NAME}</div></div>'
    f'<div class="hero-sub">{TAGLINE}</div>',
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.caption("Try one of these")
    grid = st.columns(2)
    for n, q in enumerate(EXAMPLES):
        with grid[n % 2]:
            st.button(q, on_click=set_pending, args=(q,), key=f"ex_{n}", use_container_width=True)

# ---- Chat history ----
for idx, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            if st.session_state.editing == idx:
                st.text_area("Edit your question", value=m["content"], key=f"edit_text_{idx}", label_visibility="collapsed")
                b1, b2, _ = st.columns([1, 1, 4])
                b1.button("Save", key=f"save_{idx}", on_click=save_edit, args=(idx,), type="primary")
                b2.button("Cancel", key=f"cancel_{idx}", on_click=cancel_edit)
            else:
                st.markdown(m["content"])
                st.button(
                    "Edit", key=f"editbtn_{idx}", icon=":material/edit:", type="tertiary",
                    on_click=start_edit, args=(idx,), help="Edit this question",
                )
        else:
            st.markdown(clean(m["content"]))
            if m.get("sources"):
                render_sources(m["sources"], key=f"h{idx}")
            if m.get("seconds"):
                st.caption(f"Answered in {m['seconds']:.1f}s")

# ---- Answer the new question ----
if prompt:
    with st.chat_message("assistant"):
        ok, code, warning, question = check_question(prompt)
        if ok and not session_allowed():
            ok, warning = False, MESSAGES["fast"]

        if not ok:
            st.warning(warning)
            st.session_state.messages.append({"role": "assistant", "content": warning})
            save_chat(st.session_state.chat_id, st.session_state.messages)
        else:
            start = time.time()
            slot = st.empty()
            slot.markdown(thinking_html("Searching the annual reports…"), unsafe_allow_html=True)

            answer_text, sources, error, friendly = "", [], None, False
            tab_animation(True)
            try:
                for ev in stream_events(question):
                    if ev["type"] == "sources":
                        sources = ev["sources"]
                        names = sorted({s["ticker"] for s in sources})
                        label = f"Found {len(sources)} passages in {', '.join(names)} · writing answer…"
                        slot.markdown(thinking_html(label), unsafe_allow_html=True)
                    elif ev["type"] == "status":
                        slot.markdown(thinking_html(ev["text"]), unsafe_allow_html=True)
                    elif ev["type"] == "token":
                        answer_text += ev["text"]
                        slot.markdown(clean(answer_text) + " ▌")
                    elif ev["type"] == "error":
                        error = ev["detail"]
            except UserFacingError as e:
                error, friendly = str(e), True
            except Exception as e:
                error = str(e)
            finally:
                tab_animation(False)

            if error and friendly:
                slot.warning(error)
                st.session_state.messages.append({"role": "assistant", "content": error})
                save_chat(st.session_state.chat_id, st.session_state.messages)
            elif error:
                slot.error(f"Could not get an answer. Is the API running? Details: {error}")
            else:
                seconds = time.time() - start
                slot.markdown(clean(answer_text))
                render_sources(sources, key="new")
                st.caption(f"Answered in {seconds:.1f}s")
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer_text, "sources": sources, "seconds": seconds}
                )
                save_chat(st.session_state.chat_id, st.session_state.messages)

# ---- Sidebar: chat history (built last so a new chat shows up immediately) ----
with st.sidebar:
    st.markdown(f"### {APP_NAME}")
    st.button("＋ New chat", on_click=new_chat, use_container_width=True)
    st.caption("Recent chats")
    saved = list_chats()
    if not saved:
        st.caption("Your chats will appear here." if PERSIST_CHATS else "Chats are private to this browser tab and are not saved.")
    for cid, title in saved:
        is_current = cid == st.session_state.chat_id
        c1, c2 = st.columns([6, 1])
        c1.button(
            ("● " if is_current else "") + title,
            key=f"open_{cid}",
            on_click=open_chat,
            args=(cid,),
            use_container_width=True,
        )
        c2.button("✕", key=f"del_{cid}", on_click=delete_chat, args=(cid,), help="Delete chat")