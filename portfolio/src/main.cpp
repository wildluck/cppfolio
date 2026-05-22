#define CROW_DISABLE_STATIC_DIR
#include <crow.h>
#include <crow/http_request.h>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <string>

#include <limits.h>
#include <unistd.h>

#include "generated/pages.hpp"

// directory of the running executable, so static files resolve regardless of cwd
static std::filesystem::path exe_dir()
{
    char    buf[PATH_MAX];
    ssize_t n = ::readlink("/proc/self/exe", buf, sizeof(buf));
    if (n <= 0)
        return std::filesystem::current_path();
    return std::filesystem::path(std::string(buf, static_cast<std::size_t>(n))).parent_path();
}

// helper - every page route goes through this
template<std::size_t N>
crow::response html_response(const fixed_string<N>& page)
{
    crow::response res{ 200, std::string(page.sv()) };
    res.set_header("Content-Type",    "text/html; charset=utf-8");
    res.set_header("X-Frame-Options", "DENY");
    res.set_header("Content-Security-Policy",
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'none';");
    return res;
}

int main()
{
    crow::SimpleApp app;

    CROW_ROUTE(app, "/"             )([]() { return html_response(portfolio::pages::index);         });
    CROW_ROUTE(app, "/about"        )([]() { return html_response(portfolio::pages::about);         });
    CROW_ROUTE(app, "/projects"     )([]() { return html_response(portfolio::pages::projects);      });
    CROW_ROUTE(app, "/contact"      )([]() { return html_response(portfolio::pages::contact);       });
    CROW_ROUTE(app, "/resume"       )([]() { return html_response(portfolio::pages::resume);        });
    CROW_ROUTE(app, "/uses"         )([]() { return html_response(portfolio::pages::uses);          });
    CROW_ROUTE(app, "/now"          )([]() { return html_response(portfolio::pages::now);           });
    CROW_ROUTE(app, "/testimonials" )([]() { return html_response(portfolio::pages::testimonials);  });
    CROW_ROUTE(app, "/hire"         )([]() { return html_response(portfolio::pages::hire);          });
    CROW_ROUTE(app, "/changelog"    )([]() { return html_response(portfolio::pages::changelog);     });
    CROW_ROUTE(app, "/explore"      )([]() { return html_response(portfolio::pages::explore);       });

    CROW_ROUTE(app, "/healthz")([]() {
        return crow::response{200, "ok"};
    });

    const std::filesystem::path static_dir = exe_dir() / "static";
    CROW_ROUTE(app, "/static/<path>")(
        [static_dir](const crow::request&, crow::response& res, std::string file_path) {
            crow::utility::sanitize_filename(file_path);
            res.set_static_file_info_unsafe((static_dir / file_path).string());
            res.end();
        }
    );

    CROW_CATCHALL_ROUTE(app)(
        [](const crow::request&, crow::response& res) {
            res = html_response(portfolio::pages::not_found);
            res.code = 404;
            res.end();
        }
    );

    const char*    port_env = std::getenv("PORT");
    const uint16_t port     = port_env
        ? static_cast<uint16_t>(std::stoi(port_env))
        : 8080;

    app.loglevel(crow::LogLevel::Info)
       .port(port)
       .multithreaded()
       .run();
}
