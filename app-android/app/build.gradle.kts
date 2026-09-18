import java.util.Properties

// 签名密钥与密码只在未跟踪的 local.properties（shanjian.storePassword / shanjian.keyPassword），
// 仓库里不出现明文；缺配置时跳过 release 签名（debug 包不受影响）。
val localProps = Properties().apply {
    val f = rootDir.resolve("local.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.shanjian.ai"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.shanjian.ai"
        // MediaStore RELATIVE_PATH 需要 29+；个人自用按现代手机取
        minSdk = 29
        targetSdk = 34
        versionCode = 4
        versionName = "0.1.0-mvp"
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }
    }

    signingConfigs {
        getByName("debug") {
            enableV1Signing = true
            enableV2Signing = true
        }
        create("release") {
            storeFile = file("../release.keystore")
            storePassword = localProps.getProperty("shanjian.storePassword") ?: ""
            keyAlias = "shanjian-release"
            keyPassword = localProps.getProperty("shanjian.keyPassword") ?: ""
            enableV1Signing = true
            enableV2Signing = true
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            // 没配签名（local.properties 无密码）就退回 debug 签名，保证 assembleRelease 不中断
            signingConfig = if (localProps.getProperty("shanjian.storePassword") != null)
                signingConfigs.getByName("release") else signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = false
    }
    lint {
        abortOnError = false
    }
    packaging {
        resources.excludes += setOf(
            "META-INF/INDEX.LIST",
            "META-INF/DEPENDENCIES",
            "META-INF/LICENSE",
            "META-INF/LICENSE.txt",
            "META-INF/NOTICE",
            "META-INF/NOTICE.txt",
            "META-INF/*.kotlin_module",
            "META-INF/io.netty.versions.properties"
        )
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
}
