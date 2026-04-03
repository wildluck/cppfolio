# cppfolio

> Portfolio site written in **C++23**, served by **[Crow](https://crowcpp.org)**.  
> Zero JavaScript. HTML pages are baked into the binary at compile time.

## How it works
```
data/portfolio.json          <- your personal data
templates/*.html             <- page templates with {{tokens}}
        │
        ▼  scripts/codegen.py  (Python prebuild)
        │
generated/data.hpp           <- constexpr scalars + struct arrays
generated/pages.hpp          <- fixed_string chain per page
        │
        ▼  g++ -std=c++23
        │
./cppfolio                   <- single binary, HTML inside
```

Every request returns a `std::string_view` into `.rodata`. No file I/O, no template engine, no heap allocation per request.

## Build

**Requirements:** GCC 13+ or Clang 17+, CMake 3.25+, Python 3.9+, Git
```bash
cmake -S . -B build
cmake --build build --parallel
./build/cppfolio            # listens on :8080
PORT=3000 ./build/cppfolio  # custom port
```

## Docker
```bash
docker build -t cppfolio .
docker run -p 8080:8080 cppfolio
```

## Updating content

Edit `data/portfolio.json`, then rebuild. Codegen runs automatically.

## Template tokens

| Token | Description |
|---|---|
| `{{NAME}}` | Scalar from JSON top-level key |
| `{{#each SKILLS as skill}}` | Loop over JSON array |
| `{{skill.name}}` | Field access inside loop |
| `{{#each skill.tags as tag}}` | Nested loop |
| `{{tag}}` | Leaf value (plain string array) |
| `{{include partials/nav.html}}` | Inline a partial |
| `{{meta title="X" nav="about"}}` | Page metadata |

## Project structure
```
cppfolio/
├── data/portfolio.json       <- personal data
├── templates/                <- HTML templates + partials
├── include/fixed_string.hpp  <- consteval char array type
├── scripts/codegen.py        <- prebuild code generator
├── src/main.cpp              <- Crow routes
├── CMakeLists.txt
└── Dockerfile
```

## License

MIT
