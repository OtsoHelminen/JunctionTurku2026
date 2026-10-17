interface FinnishCityAddress {
  city: string;
  streets: string[];
}

const FINNISH_CITY_ADDRESSES: FinnishCityAddress[] = [
  {
    city: 'Helsinki',
    streets: [
      'Pihlajistontie',
      'Viikinmäentie',
      'Oulunkyläntie',
      'Kivalterintie',
      'Pirjontie',
      'Paloheinäntie',
      'Suurmetsäntie',
      'Siltavoudintie',
      'Malminkaari',
      'Tapanilankaari',
    ],
  },
  {
    city: 'Espoo',
    streets: [
      'Lintuvaarantie',
      'Kilonpuistonkatu',
      'Kuitinmäentie',
      'Olarinluoma',
      'Sunankuja',
      'Saunalahdenkatu',
      'Nöykkiönkatu',
      'Jousenkaari',
      'Kaskenkaatajantie',
      'Kuusiniementie',
    ],
  },
  {
    city: 'Tampere',
    streets: [
      'Muotialantie',
      'Tesomankatu',
      'Raholankatu',
      'Peltolamminkatu',
      'Hallilantie',
      'Vuoreksenkatu',
      'Tohlopinkatu',
      'Kaukajärventie',
      'Lamminpäänkatu',
      'Lentävänniemenkatu',
    ],
  },
  {
    city: 'Turku',
    streets: [
      'Runosmäenkatu',
      'Kähärintie',
      'Halistentie',
      'Jäkärlänkaari',
      'Pansiontie',
      'Laukkavuorentie',
      'Uittamontie',
      'Nummenpuistokatu',
      'Varissuontie',
      'Pääskyvuorenrinne',
    ],
  },
  {
    city: 'Oulu',
    streets: [
      'Kaijonharjuntie',
      'Hönttämäentie',
      'Rajakyläntie',
      'Puolivälinkankaantie',
      'Metsokankaantie',
      'Pateniementie',
      'Kynsilehdontie',
      'Talvikankaantie',
      'Kiiminkipuistontie',
      'Kaakkurinkulma',
    ],
  },
  {
    city: 'Jyväskylä',
    streets: [
      'Keljonkankaantie',
      'Kuokkalantie',
      'Kortepohjantie',
      'Keltinmäentie',
      'Vaajakoskentie',
      'Säynätsalontie',
      'Huhtasuontie',
      'Tikanraitti',
      'Korpilahdentie',
      'Palokanorsi',
    ],
  },
  {
    city: 'Lahti',
    streets: [
      'Liipolankatu',
      'Kärpäsenkatu',
      'Mukkulankatu',
      'Ahtialantie',
      'Kiveriönkatu',
      'Salpausselänkatu',
      'Paavolankatu',
      'Heinlammintie',
      'Launeenkatu',
      'Hennalankatu',
    ],
  },
  {
    city: 'Kuopio',
    streets: [
      'Petosentie',
      'Neulamäentie',
      'Puijonlaaksontie',
      'Saarijärventie',
      'Jynkänkatu',
      'Lehtoniementie',
      'Inkilänmäenkatu',
      'Päivärannantie',
      'Julkulantie',
      'Särkiniementie',
    ],
  },
  {
    city: 'Pori',
    streets: [
      'Sampolantie',
      'Väinöläntie',
      'Herralahdenraitti',
      'Impolantie',
      'Pormestarinluodontie',
      'Toejoentie',
      'Ruosniementie',
      'Tikkulantie',
      'Koivistonpuistonkatu',
      'Metsämiehenkatu',
    ],
  },
  {
    city: 'Rovaniemi',
    streets: [
      'Ounasrinteentie',
      'Korkalovaarantie',
      'Saarenkyläntie',
      'Viirinkankaantie',
      'Nivavaarantie',
      'Pöykköläntie',
      'Kairatie',
      'Vaaranlammentie',
      'Koskenkyläntie',
      'Napatuntie',
    ],
  },
];

const SAMPLE_HOUSE_NUMBERS = [2, 5, 8, 11, 14, 17, 20, 23, 26, 29];

export const REAL_ESTATE_ADDRESS_SAMPLES = FINNISH_CITY_ADDRESSES.flatMap(
  ({ city, streets }) =>
    streets.map((street, index) => `${street} ${SAMPLE_HOUSE_NUMBERS[index]}, ${city}`)
);
