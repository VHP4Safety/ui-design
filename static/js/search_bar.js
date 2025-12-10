/*JS script for searchbar
*Provides search functionality*/

      function runSearch() {
        const query = document.getElementById('searchInput').value.toLowerCase().trim();

        if (!query) {
          alert('Please enter a search term.');
          return;
        }

       const pages = {
        // Tools we have
        tools: '/tools',
        'aop-builder': '/tools/aop-builder',
        aopsuite: '/tools/aopsuite',
        'aopwikiapi': '/tools/aopwikiapi',
        'aopwiki': '/tools/aopwiki',
        arrayanalysis: '/tools/arrayanalysis',
        biomodels: '/tools/biomodels',
        biotransformer: '/tools/biotransformer',
        bmdexpress_3: '/tools/bmdexpress_3',
        bridgedb: '/tools/bridgedb',
        cdkdepict: '/tools/cdkdepict',
        celldesigner: '/tools/celldesigner',
        comptox: '/tools/comptox',
        copasi: '/tools/copasi',
        cplogd: '/tools/cplogd',
        decimer: '/tools/decimer',
        ema_documents: '/tools/ema_documents',
        fairdomhub: '/tools/fairdomhub',
        fairspace: '/tools/fairspace',
        farmacokompas: '/tools/farmacokompas',
        flame: '/tools/flame',
        gscholar: '/tools/gscholar',
        google: '/tools/google',
        jrc_data_catalogue: '/tools/jrc_data_catalogue',
        llemy: '/tools/llemy',
        'mct8-dock': '/tools/mct8-dock',
        'MolAOP analyser': '/tools/MolAOP analyser',
        dsld: '/tools/dsld',
        oqt_assistant: '/tools/oqt_assistant',
        ontox_physiological_maps: '/tools/ontox_physiological_maps',
        oppbk_model: '/tools/oppbk_model',
        opsin: '/tools/opsin',
        qaop_app: '/tools/qaop_app',
        qspred: '/tools/qspred',
        sombie: '/tools/sombie',
        sysrev: '/tools/sysrev',
        oecd_qsar_toolbox: '/tools/oecd_qsar_toolbox',
        toxtemp_assistant: '/tools/toxtemp_assistant',
        txg_mapr: '/tools/txg_mapr',
        vhp_glossary: '/tools/vhp_glossary',
        wikibase: '/tools/wikibase',
        kb: '/tools/kb',
        wikipathways_aop: '/tools/wikipathways_aop',
        xploreaop: '/tools/xploreaop',

        // Case studies
        casestudies: '/casestudies',
        thyroid: '/casestudies/thyroid',
        parkinson: '/casestudies/parkinson',
        kidney: '/casestudies/kidney',

        // Data
        data: '/data',
        home: '/'
      };

        for (const key in pages) {
          if (query.includes(key)) {
            window.location.href = pages[key];
            return;
          }
        }

        alert('No results found for "' + query + '".');
      }