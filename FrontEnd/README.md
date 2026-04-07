# CloudGraph – Visual Memory Knowledge Graph

An interactive, Obsidian-style force-directed knowledge graph for photo memories.
Photos are represented as nodes that cluster dynamically based on **location**, **time period**, and **people** filters.

![CloudGraph](https://img.shields.io/badge/React-19-blue) ![Vite](https://img.shields.io/badge/Vite-8-purple)

## Features

- **Force-directed graph** with physics-based node simulation
- **Dynamic clustering** — switch between Location, Timeline, and People filters
- **Hover interactions** — tooltips reveal photo metadata and highlight connections
- **Smooth animations** — eased transitions when switching cluster modes
- **Dark, cinematic aesthetic** inspired by Obsidian's graph view
- **Canvas rendering** for 120+ nodes at 60fps

## Getting started

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The dev server runs at `http://localhost:3000`.

## Project structure

```
cloudgraph/
├── index.html
├── vite.config.js
├── package.json
└── src/
    ├── main.jsx              # Entry point
    ├── App.jsx               # Root component
    ├── index.css             # Global styles & CSS variables
    ├── components/
    │   ├── GraphCanvas.jsx   # Main canvas + render loop
    │   ├── FilterBar.jsx     # Filter toggle buttons
    │   ├── Legend.jsx         # Cluster color legend
    │   ├── Tooltip.jsx        # Hover tooltip
    │   └── StatsPanel.jsx     # Photo/connection/cluster counts
    ├── data/
    │   └── photos.js         # Sample data generation
    └── hooks/
        └── useForceSimulation.js  # Force-directed physics engine
```

## Deployment

- **AWS Amplify**: Connect your repo to the Amplify console and use `npm run build`.
  - > [!NOTE]
  - > **Student Accounts**: Amplify often fails due to IAM role restrictions. If so, use the local hosting method below.
- **Vercel / Netlify**: Connect your GitHub repo and set the build command to `npm run build` and output directory to `dist/`.
- **Local Production Host**: Run `npm run build` then `npm run preview` to host the optimized build on your own machine (useful for testing with the live cloud backend).

## Customization

- **Photo count**: Change the argument in `generatePhotos(120)` inside `GraphCanvas.jsx`
- **Cluster categories**: Edit `locations`, `timePeriods`, and `people` arrays in `src/data/photos.js`
- **Colors**: Modify CSS variables in `src/index.css` or cluster color values in `photos.js`
- **Physics**: Tune repulsion, spring, and damping constants in `useForceSimulation.js`

## Next steps for CloudGraph

- Replace colored dots with circular-clipped photo thumbnails
- Integrate Google MediaPipe for hand gesture navigation
- Connect to AWS backend (Cognito auth, S3 photo storage, RDS metadata)
- Add search bar with fuzzy matching across photo metadata
- Implement zoom/pan with mouse wheel and drag
