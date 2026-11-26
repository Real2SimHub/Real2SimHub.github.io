# Real2SimHub website

The static site of [Real2SimHub](https://real2simhub.github.io/): a community to build the
infrastructure of real-to-simulation together. Plain HTML, CSS and a little JavaScript; no build step is needed to
serve it (GitHub Pages serves the repository root as is).

```text
data/site.json          every URL, the arXiv ID, the paper title, authors and affiliations,
                        the project cards and the "Discover our research" rows
pages/*.html            page bodies with {{placeholders}} (home, one file per project)
scripts/build.py        fills the pages from data/site.json -> index.html, <project>/index.html, 404.html
assets/                 CSS, JS, the brand kit, card images, paper figures, the video and its poster
video/                  the Real2SimHub video: scenes as HTML pages and the script that renders them
scripts/prepare_assets.py   regenerates the committed images from the paper and the projects
scripts/check_links.py      offline check: local links, anchors, alt text, wording
scripts/screenshots.mjs     screenshots at 1440 and 390 px, light and dark, with page checks
```

## Common changes

- **arXiv ID, URLs, authors**: edit `data/site.json` (`paper.arxiv_id`, `links`, `paper.authors`,
  `paper.affiliations`), then run `python3 scripts/build.py`. While `arxiv_id` is empty, every
  arXiv button shows "coming soon" and the BibTeX uses `XXXX.XXXXX`.
- **A new project**: add an entry to `projects` (and a row to `research`) in `data/site.json`,
  write its body as `pages/<slug>.html`, draw its logo (`PROJECTS` in `scripts/make_brand.py`, see
  [assets/brand/README.md](assets/brand/README.md)), and run `python3 scripts/build.py`. Its tab appears
  in the header of every page.
- **The project cards' figures**: each card shows its project's README figure (light and dark), whole on wide
  screens and its middle box on phones; `python3 scripts/prepare_assets.py --only cards` cuts them from the
  Lab and Awesome checkouts (`OVERVIEWS` holds the boxes) and also makes the small card in the header of the
  Awesome page (panel 3 of the paper's Figure 1).

## Build and check

```bash
python3 scripts/build.py            # regenerate the pages
python3 scripts/build.py --check    # fails if a generated page is out of date
python3 scripts/check_links.py      # local links, anchors, alt text, wording
python3 -m http.server 8000         # preview at http://localhost:8000
node scripts/screenshots.mjs /tmp/shots   # optional: needs node 22+ and google-chrome
```

## The video

`assets/video/real2simhub.mp4` (1920x1080, 30 fps, H.264 and AAC, narrated in English over music), shown on the home
page, is rendered from `video/scenes/*.html` by `python3 video/make_video.py`, after `python video/narrate.py` has
synthesised the narration (`video/narration.json`) locally with Kokoro-82M. It needs ffmpeg, node 22+, google-chrome,
the Noto Sans fonts, a Python with `kokoro` for the narration, and the sources named in `video/make_video.py`.

## Credits

The footer of every page links here. Frames of physical events: Physics-IQ (CC-BY-4.0), IRIS (CC-BY-NC-4.0), PhysCodeGym's clip of a
Physics-IQ take, PhySimCode (MIT), Video2World's Push-T sample (MIT), DROID (CC-BY-4.0, through Video2World). Simulations are
re-runs of programs written by the Codex agent with Real2SimLab. 4DCodeBench declares no license for its code and data, so no frame
of its data appears in the video or in our own figures.
Product names and logos identify the agents, benchmarks and institutions only; no endorsement is implied.

Sound of the video: the narration is synthesised with [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0,
voice `af_heart`). Music: 'Supernova' by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au
([the track's page](https://www.scottbuckley.com.au/library/supernova/),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)); edited to the video on its beat grid (only its first half
and its light breakdown, none of the heavy bass of its second half), louder between the lines and lowered under
the narration (`video/music.json`, `video/make_video.py`).

Figures in the blog posts on other people's work come from their papers, each credited in its caption; each post's
card on the home and blog pages is a crop of one of them. Under arXiv's non-exclusive distribution license, reproduced
with credit to the authors:

- 4DCodeBench, Shen, Kovačič, Kulits et al., [arXiv:2610.03715](https://arxiv.org/abs/2610.03715): Figures 1 and 3.
- Physics-IQ, Motamed, Culp, Swersky, Jaini and Geirhos, [arXiv:2501.09038](https://arxiv.org/abs/2501.09038): the
  protocol figure (Figure 2) and the switch frames of all scenarios (Figure 9, appendix), which show frames of the Physics-IQ
  dataset ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
- PhySimCode, Kundu, Gupta, Julin, Zhao, Xie and Jeni, [arXiv:2610.15722](https://arxiv.org/abs/2610.15722): the
  domain chart (Figure 1) and the renders of closed-source models' programs (appendix).

Under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (trimmed of white margins and resized):

- IRIS, Khanbayov, Barhdadi, Serpedin and Kurban, [arXiv:2603.16432](https://arxiv.org/abs/2603.16432): Figure 1.
- PhysCodeGym, Shao, He, Fan, Guo et al., [arXiv:2610.17288](https://arxiv.org/abs/2610.17288): Figures 1 and 2.
- Agentic Real2Sim, Chen, Xia, Peng, Zhang et al., [arXiv:2607.19190](https://arxiv.org/abs/2607.19190): Figures 1
  and 2.
- 3DCodeVerse, Gao, Zeng, Huang, Li et al., [arXiv:2610.22341](https://arxiv.org/abs/2610.22341): Figures 1
  and 3.

Under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/): Video2World, Tang, Zhang, Yang et al.,
[arXiv:2610.04432](https://arxiv.org/abs/2610.04432), Figures 1 and 2.

The wall of real recordings in the video (`video/real_clips.json`) also uses these files from Wikimedia Commons, each shrunk
to a tile and shown as recorded and as building blocks:

- [Ocean surface waves 02](https://commons.wikimedia.org/wiki/File:Ocean_surface_waves_02.ogv): Mostafameraji, CC0
- [DiagonalCrosswalkYongeDundas](https://commons.wikimedia.org/wiki/File:DiagonalCrosswalkYongeDundas.webm): Raysonho @ Open Grid Scheduler / Grid Engine, CC0
- [Cat playing in Taiwan](https://commons.wikimedia.org/wiki/File:Cat_playing_in_Taiwan.webm): MiNe, CC BY 2.0
- [Robot package handling](https://commons.wikimedia.org/wiki/File:Robot_package_handling.webm): newscreators, CC BY 3.0
- [Timelapse of Clouds over Bellevue Canyon](https://commons.wikimedia.org/wiki/File:Timelapse_of_Clouds_over_Bellevue_Canyon.webm): Extemporalist, CC0
- [A grazing horse at the Écomusée de la Bintinais](https://commons.wikimedia.org/wiki/File:A_grazing_horse_at_the_%C3%89comus%C3%A9e_de_la_Bintinais.webm): Seb35, CC0
- [Strider Robot Climbing - 12 leg Version](https://commons.wikimedia.org/wiki/File:Strider_Robot_Climbing_-_12_leg_Version.webm): DIY Walkers, CC BY 3.0
- [Moccamaster coffee maker](https://commons.wikimedia.org/wiki/File:Moccamaster_coffee_maker.webm): Erik Pålsson, CC BY 3.0
- [Rain in Sonoma - December 2025 - Sarah Stierch](https://commons.wikimedia.org/wiki/File:Rain_in_Sonoma_-_December_2025_-_Sarah_Stierch.webm): Missvain, CC0
- [Pollen Robotics - Reachy is back...and it's mobile!](https://commons.wikimedia.org/wiki/File:Pollen_Robotics_-_Reachy_is_back...and_it%27s_mobile!.webm): Pollen Robotics, CC BY 3.0
- [Burning PET bottle](https://commons.wikimedia.org/wiki/File:Burning_PET_bottle.ogv): 01x07x2022000, CC0
- [Traffic on a cobbled street - soundscape](https://commons.wikimedia.org/wiki/File:Traffic_on_a_cobbled_street_-_soundscape.webm): Sounds of Changes, CC BY 3.0
- [Young seagull calling](https://commons.wikimedia.org/wiki/File:Young_seagull_calling.webm): Andy Li, CC0
- [Robot arm R1 operation of the autonomous laboratory for the accelerated synthesis of novel materials (handling powders and slurries in the sample preparation station)](https://commons.wikimedia.org/wiki/File:Robot_arm_R1_operation_of_the_autonomous_laboratory_for_the_accelerated_synthesis_of_novel_materials_%28handling_powders_and_slurries_in_the_sample_preparation_station%29.webm): Nathan J. Szymanski et al., CC BY 4.0
- [Video fountain Lützowplatz Eberhard Fink Berlin-Tiergarten](https://commons.wikimedia.org/wiki/File:Video_fountain_L%C3%BCtzowplatz_Eberhard_Fink_Berlin-Tiergarten.webm): Singlespeedfahrer, CC0
- [Snow falling in Charlton MA 2025-12-14](https://commons.wikimedia.org/wiki/File:Snow_falling_in_Charlton_MA_2025-12-14.webm): Peter Cooper Jr., CC0

Institution logos (`assets/img/orgs/`): from each institution's own website or its Wikipedia file page (the sources are
listed in Awesome-Real2Sim's `data/institutions.json`); Southeast University's emblem from www.seu.edu.cn; the UESTC AI Club
logo from the club; Ngoro Robotics' wordmark is redrawn as a vector from a photo of the company's own logo; the National
University of Singapore's coat of arms from its [Wikipedia file page](https://en.wikipedia.org/wiki/File:NUS_coat_of_arms.svg);
the University of Rochester's shield from the site icon of www.rochester.edu ("URochester" is the university's own short form).
UC San Diego's seal from its [Wikimedia Commons file page](https://commons.wikimedia.org/wiki/File:Seal_of_the_University_of_California,_San_Diego.svg)
(public domain), rendered on white; AgiBot's symbol from the company's logo on www.zhiyuan-robot.com.
