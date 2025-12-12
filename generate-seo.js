const fs = require('fs');
const https = require('https');

// Configuration
const SOURCE_URL = 'https://raw.githubusercontent.com/albinchristo04/ptv/refs/heads/main/events.json';
const OUTPUT_FILE = 'seo-metadata.json';
const DOMAIN = 'https://tarjetarojaenvivo.live';

// Primary Spanish keywords for Bing optimization
const PRIMARY_KEYWORDS = [
  'rojadirecta',
  'tarjeta roja',
  'rojadirecta tv',
  'pirlotv',
  'tarjeta roja tv',
  'rojadirecta en vivo',
  'tarjeta roja directa',
  'tarjeta roja en vivo',
  'pirlo tv rojadirecta',
  'roja directa pirlo',
  'tarjeta roja futbol en vivo',
  'roja directa en vivo fútbol gratis',
  'tarjeta roja fútbol en vivo',
  'pirlo tv tarjeta roja',
  'tarjeta roja tv en vivo',
  'roja tv',
  'la roja directa',
  'rojadirecta tv en vivo',
  'roja dirécta'
];

// Fetch JSON data
function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

// Generate SEO-friendly slug
function generateSlug(text) {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remove accents
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Translate category names to Spanish
function translateCategory(category) {
  const translations = {
    'American Football': 'Fútbol Americano',
    'Basketball': 'Baloncesto',
    'Combat Sports': 'Deportes de Combate',
    'Darts': 'Dardos',
    'Football': 'Fútbol',
    'Ice Hockey': 'Hockey sobre Hielo',
    'Wrestling': 'Lucha Libre',
    '24/7 Streams': 'Transmisiones 24/7'
  };
  return translations[category] || category;
}

// Get Spanish month name
function getSpanishMonth(month) {
  const months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  return months[month];
}

// Get Spanish day name
function getSpanishDay(day) {
  const days = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
  return days[day];
}

// Format date in Spanish
function formatSpanishDate(timestamp) {
  const date = new Date(timestamp * 1000);
  const day = getSpanishDay(date.getDay());
  const dayNum = date.getDate();
  const month = getSpanishMonth(date.getMonth());
  const year = date.getFullYear();
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  
  return {
    full: `${day} ${dayNum} de ${month} de ${year}`,
    short: `${dayNum} de ${month} de ${year}`,
    time: `${hours}:${minutes}`,
    iso: date.toISOString()
  };
}

// Format date for SEO
function formatDate(timestamp) {
  const date = new Date(timestamp * 1000);
  return date.toISOString();
}

// Generate rich metadata for each event
function generateMetadata(stream, category) {
  const {
    id,
    name,
    tag,
    poster,
    uri_name,
    starts_at,
    ends_at,
    category_name,
    viewers
  } = stream;

  const eventDate = formatSpanishDate(starts_at);
  const endDate = formatSpanishDate(ends_at);
  const slug = generateSlug(name);
  const categorySpanish = translateCategory(category_name);

  // Extract teams/competitors from name
  const teams = name.split(' vs. ').map(t => t.trim());
  const isVersusMatch = teams.length === 2;

  // Build keyword list with primary keywords + event-specific terms
  const eventKeywords = [
    ...PRIMARY_KEYWORDS.slice(0, 8), // Top 8 primary keywords
    name,
    ...teams,
    categorySpanish,
    category_name,
    'ver online gratis',
    'en vivo gratis',
    'streaming gratis',
    tag,
    eventDate.short,
    'transmisión en vivo'
  ];

  // Generate comprehensive SEO metadata in Spanish
  return {
    // Basic Info
    id,
    slug,
    uri_name,
    canonical_url: `${DOMAIN}/eventos/${uri_name}`,

    // SEO Meta Tags (Spanish, optimized for Bing)
    meta: {
      title: `${name} EN VIVO - Tarjeta Roja TV | Rojadirecta Gratis`,
      description: `⚽ Ver ${name} en vivo gratis por Tarjeta Roja TV. ${isVersusMatch ? `${teams[0]} vs ${teams[1]}` : name} transmisión en directo ${eventDate.full}. Rojadirecta, Pirlo TV - Fútbol gratis online.`,
      keywords: eventKeywords.join(', '),
      robots: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1',
      author: 'Tarjeta Roja En Vivo',
      viewport: 'width=device-width, initial-scale=1.0',
      language: 'es',
      'geo.region': 'ES',
      'geo.placename': 'España',
      rating: 'general',
      revisit_after: '1 hour',
      'msapplication-TileColor': '#e31937',
      'theme-color': '#e31937'
    },

    // Open Graph (Facebook, LinkedIn) - Spanish
    og: {
      type: 'website',
      url: `${DOMAIN}/eventos/${uri_name}`,
      title: `${name} EN VIVO ⚽ Tarjeta Roja TV - Rojadirecta Gratis`,
      description: `Ver ${name} en vivo gratis. ${isVersusMatch ? `${teams[0]} vs ${teams[1]}` : name} transmisión en directo por Tarjeta Roja TV - ${eventDate.full} a las ${eventDate.time}hrs.`,
      image: poster,
      image_alt: `${name} - Tarjeta Roja TV en vivo`,
      site_name: 'Tarjeta Roja En Vivo - Rojadirecta TV',
      locale: 'es_ES',
      locale_alternate: ['es_MX', 'es_AR', 'es_CO', 'es_CL']
    },

    // Twitter Card - Spanish
    twitter: {
      card: 'summary_large_image',
      site: '@tarjetarojatvs',
      title: `${name} EN VIVO ⚽ Tarjeta Roja - Rojadirecta`,
      description: `Ver ${name} en vivo gratis por Tarjeta Roja TV. ${categorySpanish} en directo.`,
      image: poster,
      image_alt: `${name} streaming gratis`,
      creator: '@tarjetarojatvs'
    },

    // Schema.org JSON-LD for Rich Results (Spanish)
    schema: {
      '@context': 'https://schema.org',
      '@type': 'SportsEvent',
      name: name,
      description: `Transmisión en vivo de ${name} gratis por Tarjeta Roja TV`,
      startDate: eventDate.iso,
      endDate: endDate.iso,
      eventStatus: 'https://schema.org/EventScheduled',
      eventAttendanceMode: 'https://schema.org/OnlineEventAttendanceMode',
      location: {
        '@type': 'VirtualLocation',
        url: `${DOMAIN}/eventos/${uri_name}`,
        name: 'Tarjeta Roja En Vivo'
      },
      image: [poster],
      organizer: {
        '@type': 'Organization',
        name: 'Tarjeta Roja En Vivo',
        url: DOMAIN,
        logo: `${DOMAIN}/logo.png`,
        sameAs: [
          'https://www.facebook.com/tarjetarojaenvivo',
          'https://twitter.com/tarjetarojatvs'
        ]
      },
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'EUR',
        availability: 'https://schema.org/InStock',
        url: `${DOMAIN}/eventos/${uri_name}`,
        validFrom: eventDate.iso
      },
      ...(isVersusMatch && {
        competitor: teams.map(team => ({
          '@type': 'SportsTeam',
          name: team
        })),
        homeTeam: {
          '@type': 'SportsTeam',
          name: teams[0]
        },
        awayTeam: {
          '@type': 'SportsTeam',
          name: teams[1]
        }
      }),
      sport: categorySpanish,
      inLanguage: 'es'
    },

    // Additional SEO Elements (Spanish)
    seo: {
      breadcrumbs: [
        { name: 'Inicio', url: DOMAIN },
        { name: categorySpanish, url: `${DOMAIN}/categoria/${generateSlug(categorySpanish)}` },
        { name: name, url: `${DOMAIN}/eventos/${uri_name}` }
      ],
      h1: `${name} EN VIVO - Tarjeta Roja TV`,
      h2: `Ver ${name} Online Gratis por Rojadirecta`,
      faq: [
        {
          question: `¿Cómo ver ${name} en vivo gratis?`,
          answer: `Puedes ver ${name} en vivo gratis por Tarjeta Roja TV. La transmisión comienza el ${eventDate.full} a las ${eventDate.time}hrs. Rojadirecta y Pirlo TV transmiten en directo.`
        },
        {
          question: `¿A qué hora es ${name}?`,
          answer: `${name} comienza el ${eventDate.full} a las ${eventDate.time}hrs (hora de España).`
        },
        {
          question: `¿Dónde ver ${name} por internet?`,
          answer: `Ver ${name} online por Tarjeta Roja TV, Rojadirecta, y Pirlo TV. Transmisión gratis en vivo sin registro.`
        },
        ...(isVersusMatch ? [{
          question: `¿Dónde ver ${teams[0]} vs ${teams[1]} en vivo?`,
          answer: `Ver ${teams[0]} vs ${teams[1]} en directo por Tarjeta Roja, Rojadirecta TV y Pirlo TV. Streaming gratis de ${categorySpanish}.`
        }] : []),
        {
          question: '¿Qué es Tarjeta Roja TV?',
          answer: 'Tarjeta Roja TV (también conocida como Rojadirecta, Pirlo TV) es una plataforma para ver deportes en vivo gratis. Transmisión de fútbol, baloncesto, UFC y más deportes online.'
        },
        {
          question: '¿Es gratis Tarjeta Roja?',
          answer: 'Sí, Tarjeta Roja TV es completamente gratis. Ver todos los partidos en vivo sin pagar, sin registro y sin publicidad invasiva.'
        }
      ],
      content_sections: [
        {
          heading: `Ver ${name} en Vivo Gratis`,
          content: `Transmisión en directo de ${name} por Tarjeta Roja TV. ${isVersusMatch ? `${teams[0]} se enfrenta a ${teams[1]}` : name} el ${eventDate.full}. Rojadirecta y Pirlo TV ofrecen streaming gratis de ${categorySpanish}.`
        },
        {
          heading: `${name} - Tarjeta Roja Directa`,
          content: `Ver ${name} online gratis. La Roja Directa transmite ${categorySpanish} en vivo sin cortes. Rojadirecta TV, Pirlo TV y Tarjeta Roja son tu mejor opción para ver deportes gratis.`
        }
      ]
    },

    // Event Details (bilingual)
    event: {
      name,
      name_es: name,
      category: category_name,
      category_es: categorySpanish,
      broadcaster: tag,
      start_time: eventDate.iso,
      start_time_formatted: `${eventDate.full} - ${eventDate.time}hrs`,
      end_time: endDate.iso,
      duration_minutes: Math.round((ends_at - starts_at) / 60),
      status: starts_at < Date.now() / 1000 ? (ends_at > Date.now() / 1000 ? 'en vivo' : 'finalizado') : 'próximamente',
      viewers: viewers || '0',
      language: 'es',
      country_focus: ['ES', 'MX', 'AR', 'CO', 'CL', 'PE', 'VE', 'EC'],
      ...(isVersusMatch && {
        home_team: teams[0],
        away_team: teams[1],
        match_type: 'vs',
        match_title: `${teams[0]} vs ${teams[1]}`
      })
    },

    // Technical SEO (Bing optimized)
    technical: {
      last_modified: new Date().toISOString(),
      priority: stream.always_live ? 0.9 : 0.85,
      changefreq: stream.always_live ? 'always' : 'hourly',
      hreflang: 'es',
      alternate_languages: {
        'es-ES': `${DOMAIN}/eventos/${uri_name}`,
        'es-MX': `${DOMAIN}/mx/eventos/${uri_name}`,
        'es-AR': `${DOMAIN}/ar/eventos/${uri_name}`
      }
    },

    // Bing-specific optimizations
    bing: {
      verify: 'bing-site-verification-code',
      news_keywords: eventKeywords.slice(0, 10).join(', '),
      content_type: 'Sports',
      syndication_source: DOMAIN,
      original_source: DOMAIN,
      content_language: 'es',
      geo_region: 'ES',
      distribution: 'global',
      audience: 'all',
      rating: 'general'
    }
  };
}

// Main function
async function generateSEOData() {
  try {
    console.log('Fetching events data...');
    const data = await fetchJSON(SOURCE_URL);

    if (!data.events || !data.events.streams) {
      throw new Error('Invalid data structure');
    }

    const seoData = {
      generated_at: new Date().toISOString(),
      total_events: 0,
      categories: [],
      events: []
    };

    // Process each category
    for (const category of data.events.streams) {
      const categorySpanish = translateCategory(category.category);
      
      const categoryMeta = {
        id: category.id,
        name: category.category,
        name_es: categorySpanish,
        slug: generateSlug(category.category),
        event_count: category.streams.length,
        always_live: category.always_live,
        canonical_url: `${DOMAIN}/categoria/${generateSlug(categorySpanish)}`,
        meta: {
          title: `${categorySpanish} EN VIVO - Tarjeta Roja TV | Rojadirecta Gratis`,
          description: `⚽ Ver ${categorySpanish} en vivo gratis por Tarjeta Roja TV. Todos los partidos y eventos de ${categorySpanish} online. Rojadirecta, Pirlo TV - Streaming gratis.`,
          keywords: [
            ...PRIMARY_KEYWORDS.slice(0, 10),
            categorySpanish,
            category.category,
            `${categorySpanish} en vivo`,
            `ver ${categorySpanish} gratis`,
            `${categorySpanish} online`
          ].join(', ')
        },
        schema: {
          '@context': 'https://schema.org',
          '@type': 'CollectionPage',
          name: `${categorySpanish} en Vivo - Tarjeta Roja TV`,
          description: `Ver todos los eventos de ${categorySpanish} en vivo gratis`,
          url: `${DOMAIN}/categoria/${generateSlug(categorySpanish)}`,
          inLanguage: 'es'
        }
      };

      seoData.categories.push(categoryMeta);

      // Process each stream in category
      for (const stream of category.streams) {
        const eventMeta = generateMetadata(stream, category.category);
        seoData.events.push(eventMeta);
        seoData.total_events++;
      }
    }

    // Write to file
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(seoData, null, 2));
    console.log(`✅ Generated SEO metadata for ${seoData.total_events} events`);
    console.log(`📁 Output saved to: ${OUTPUT_FILE}`);

    // Generate sitemap URLs with Spanish priorities
    const sitemapUrls = [
      // Homepage - highest priority
      {
        loc: DOMAIN,
        lastmod: new Date().toISOString(),
        changefreq: 'always',
        priority: 1.0,
        'xhtml:link': [
          { rel: 'alternate', hreflang: 'es', href: DOMAIN },
          { rel: 'alternate', hreflang: 'es-ES', href: DOMAIN },
          { rel: 'alternate', hreflang: 'es-MX', href: `${DOMAIN}/mx` },
          { rel: 'alternate', hreflang: 'x-default', href: DOMAIN }
        ]
      },
      // Category pages
      ...seoData.categories.map(c => ({
        loc: c.canonical_url,
        lastmod: new Date().toISOString(),
        changefreq: 'hourly',
        priority: 0.9
      })),
      // Event pages
      ...seoData.events.map(e => ({
        loc: e.canonical_url,
        lastmod: e.technical.last_modified,
        changefreq: e.technical.changefreq,
        priority: e.technical.priority
      }))
    ];

    fs.writeFileSync('sitemap-urls.json', JSON.stringify(sitemapUrls, null, 2));
    console.log(`🗺️  Generated sitemap URLs: sitemap-urls.json`);

    // Generate keywords file for Bing Webmaster Tools
    const keywordData = {
      primary_keywords: PRIMARY_KEYWORDS,
      total_keywords: PRIMARY_KEYWORDS.length,
      target_audience: 'Spanish speakers (Spain, Mexico, Argentina, Colombia)',
      target_search_engines: ['Bing', 'Google'],
      language: 'es',
      generated_at: new Date().toISOString()
    };

    fs.writeFileSync('keywords.json', JSON.stringify(keywordData, null, 2));
    console.log(`🔑 Generated keywords file: keywords.json`);

    return seoData;
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

// Run the generator
if (require.main === module) {
  generateSEOData();
}

module.exports = { generateSEOData, generateMetadata };
