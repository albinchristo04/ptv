const fs = require('fs');
const https = require('https');

// Configuration
const SOURCE_URL = 'https://raw.githubusercontent.com/albinchristo04/ptv/refs/heads/main/events.json';
const OUTPUT_FILE = 'seo-metadata.json';

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
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
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

  const eventDate = new Date(starts_at * 1000);
  const endDate = new Date(ends_at * 1000);
  const slug = generateSlug(name);

  // Extract teams/competitors from name
  const teams = name.split(' vs. ').map(t => t.trim());
  const isVersusMatch = teams.length === 2;

  // Generate comprehensive SEO metadata
  return {
    // Basic Info
    id,
    slug,
    uri_name,
    canonical_url: `https://yourdomain.com/events/${uri_name}`,

    // SEO Meta Tags
    meta: {
      title: `${name} - Live Stream | ${category_name}`,
      description: `Watch ${name} live stream. ${isVersusMatch ? `${teams[0]} takes on ${teams[1]}` : name} on ${eventDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}. Free live streaming of ${category_name}.`,
      keywords: [
        name,
        ...teams,
        category_name,
        'live stream',
        'watch online',
        'free streaming',
        tag,
        'live coverage',
        eventDate.getFullYear().toString()
      ].join(', '),
      robots: 'index, follow',
      author: 'Your Site Name',
      viewport: 'width=device-width, initial-scale=1.0'
    },

    // Open Graph (Facebook, LinkedIn)
    og: {
      type: 'website',
      url: `https://yourdomain.com/events/${uri_name}`,
      title: `${name} - Live Stream`,
      description: `Watch ${name} live. ${isVersusMatch ? `${teams[0]} vs ${teams[1]}` : name} streaming live on ${eventDate.toLocaleDateString()}.`,
      image: poster,
      site_name: 'Your Sports Streaming Site',
      locale: stream.locale === 'en' ? 'en_US' : stream.locale === 'fr' ? 'fr_FR' : 'en_US'
    },

    // Twitter Card
    twitter: {
      card: 'summary_large_image',
      site: '@yourhandle',
      title: `${name} - Live Stream`,
      description: `Watch ${name} live stream online. ${category_name} coverage.`,
      image: poster,
      creator: '@yourhandle'
    },

    // Schema.org JSON-LD for Rich Results
    schema: {
      '@context': 'https://schema.org',
      '@type': 'SportsEvent',
      name: name,
      description: `Live streaming of ${name}`,
      startDate: formatDate(starts_at),
      endDate: formatDate(ends_at),
      eventStatus: 'https://schema.org/EventScheduled',
      eventAttendanceMode: 'https://schema.org/OnlineEventAttendanceMode',
      location: {
        '@type': 'VirtualLocation',
        url: `https://yourdomain.com/events/${uri_name}`
      },
      image: poster,
      organizer: {
        '@type': 'Organization',
        name: 'Your Site Name',
        url: 'https://yourdomain.com'
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
      sport: category_name
    },

    // Additional SEO Elements
    seo: {
      breadcrumbs: [
        { name: 'Home', url: 'https://yourdomain.com' },
        { name: category_name, url: `https://yourdomain.com/category/${generateSlug(category_name)}` },
        { name: name, url: `https://yourdomain.com/events/${uri_name}` }
      ],
      h1: name,
      h2: `Watch ${name} Live Stream Online`,
      faq: [
        {
          question: `How to watch ${name} live?`,
          answer: `You can watch ${name} live stream on our platform. The event starts on ${eventDate.toLocaleDateString()} at ${eventDate.toLocaleTimeString()}.`
        },
        {
          question: `What time does ${name} start?`,
          answer: `${name} starts at ${eventDate.toLocaleTimeString()} on ${eventDate.toLocaleDateString()}.`
        },
        ...(isVersusMatch ? [{
          question: `Where to watch ${teams[0]} vs ${teams[1]}?`,
          answer: `Watch ${teams[0]} vs ${teams[1]} live stream here. Free online streaming available.`
        }] : [])
      ]
    },

    // Event Details
    event: {
      name,
      category: category_name,
      broadcaster: tag,
      start_time: formatDate(starts_at),
      end_time: formatDate(ends_at),
      duration_minutes: Math.round((ends_at - starts_at) / 60),
      status: starts_at < Date.now() / 1000 ? (ends_at > Date.now() / 1000 ? 'live' : 'completed') : 'upcoming',
      viewers: viewers || '0',
      language: stream.locale,
      ...(isVersusMatch && {
        home_team: teams[0],
        away_team: teams[1],
        match_type: 'vs'
      })
    },

    // Technical SEO
    technical: {
      last_modified: new Date().toISOString(),
      priority: stream.always_live ? 0.9 : 0.8,
      changefreq: stream.always_live ? 'always' : 'daily',
      hreflang: stream.locale === 'en' ? 'en' : stream.locale === 'fr' ? 'fr' : 'en'
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
      const categoryMeta = {
        id: category.id,
        name: category.category,
        slug: generateSlug(category.category),
        event_count: category.streams.length,
        always_live: category.always_live,
        meta: {
          title: `${category.category} Live Streams - Watch Online`,
          description: `Watch ${category.category} live streams online. Free streaming of all ${category.category} events, matches, and games.`,
          keywords: `${category.category}, live stream, watch online, free streaming`
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

    // Generate sitemap URLs
    const sitemapUrls = seoData.events.map(e => ({
      loc: e.canonical_url,
      lastmod: e.technical.last_modified,
      changefreq: e.technical.changefreq,
      priority: e.technical.priority
    }));

    fs.writeFileSync('sitemap-urls.json', JSON.stringify(sitemapUrls, null, 2));
    console.log(`🗺️  Generated sitemap URLs: sitemap-urls.json`);

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
