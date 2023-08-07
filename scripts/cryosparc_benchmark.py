#
# cryoSPARC Benchmark v2.0
# (c) Structura Biotechnology Inc 2020
# Requires cryoSPARC v2.15.0+
#
# Benchmark Launch Script
# ------------------------------------------------------------------------------------------------
# This should be called after 
# eval $(bin/cryosparcm env)
# so that all necessary environment variables are set and the correct python will be used.
#
#
# USAGE
# The following will take place on the master node itself:
# 1) locate the install path where you have installed cryosparc2_master
#    In the install directory, you will find bin/cryosparcm
#    E.g. `/home/cryosparc_user/cryosparc2_master/bin/cryosparcm`
# 2) Determine the hostname of the node where the benchmark jobs will run
# 3) Determine the GPU-ID number of the GPU you wish to run the benchmark on.
#    Note that `nvidia_smi` indices do not always correspond to CUDA indices.
# 4) Determine the hostname and port number where cryosparc2_master is running
#    This can be done using cryosparcm status on the master node. 
#    The port number is 39000 by default.
# 5) With the master process running, create a project in cryosparc 2 (thereby selecting
#    a project directory, where intermediate and final results will be stored). Ensure
#    it is on fast disks for accurate timings. Note the project UID ("PXXXX")
# 5) Download the benchmark_data.tar.gz and unpack it somewhere. Make sure
#    it is on a fast SSD to get accurate timings.
# 6) Place this script anywhere you like.
#
# Now, in a shell:
#
# $ eval ($</path/to/bin/cryosparcm> env)
# $ python cryosparc2_benchmark.py --master_hostname < master_hostname > 
#                                  --port 39000 
#                                  --worker_hostname < worker_hostname > 
#                                  --gpus 0 [,1,2,3]
#                                  --input_data_dir "abs/path/to/benchmark_data" 
#                                  --project_uid "P22" 
#                                  --user_email < email>
#                                  --mode <"preprocess", "reconstruct">
#                                  --dataset <10028, 10025>
#                                  --out "./path/to/output_dir"
#
# The script will sequentially create and run all the jobs in the benchmark.
# Timings will be displayed and also dumped into the specified output.json file.
# At any point, you can kill this script with ctrl+C and the running job will 
# also be killed. All jobs will be created within the project that you 
# specified, in a new workspace stamped with the worker_hostname and current 
# datetime.

import os, sys

sys.path.append(os.environ['CRYOSPARC_ROOT_DIR'])
import cryosparc_compute.jobs.runcommon as rc

from collections import OrderedDict, defaultdict
import argparse
import time
import datetime
import json
import errno

cli = None
db = None

def get_benchmark_jobs_dict(input_data_dir = "/", job_types_only=False, dataset_selected=None, datasets_only=False, modes_only=False):
    '''
    This dictionary holds all the jobs and their parameters required to run for the actual benchmark.

    :param input_data_dir: the directory user specified where the benchmark data is located
    :type input_data_dir: str
    '''
    benchmark_jobs = {
        'preprocess' : {
            10028 : [
                {
                    'setup_requires' : [],
                    'advanced' : False,
                    'key' : 'import_movies_1',
                    'job_type' : 'import_movies',
                    'job_title' : "Import Movies 1",
                    'params' : {
                        'blob_paths' : os.path.join(input_data_dir, 'data/Micrographs/Micrographs_part1/*.mrcs'),
                        'psize_A' : 1.03,
                        'accel_kv' : 300,
                        'cs_mm' : 2.7,
                        'total_dose_e_per_A2' : 100,
                    },
                    'timeout' : 1800
                },
                {
                    'setup_requires' : [],
                    'advanced' : False,
                    'key' : 'import_movies_2', 
                    'job_type' : 'import_movies', 
                    'job_title' : 'Import Movies 2', 
                    'params' : {
                        'blob_paths' : os.path.join(input_data_dir, 'data/Micrographs/Micrographs_part2/*.mrcs'),
                        'psize_A' : 1.03,
                        'accel_kv' : 300,
                        'cs_mm' : 2.7,
                        'total_dose_e_per_A2' : 100,
                    },
                    'timeout' : 1800
                },
                {
                    'setup_requires' : ['import_movies_1', 'import_movies_2'],
                    'advanced' : False,
                    'key' : 'patch_motion', 
                    'job_type' : 'patch_motion_correction_multi', 
                    'job_title' : 'Patch Motion Correction', 
                    'params' : {
                        'do_plots' : False
                    },
                    'input_group_connects' : { 
                        'movies' : [
                            {
                                'input_job_name' : 'import_movies_1',
                                'group_name' : 'imported_movies'
                            },
                            {
                                'input_job_name' : 'import_movies_2',
                                'group_name' : 'imported_movies'
                            }
                        ] 
                    }
                },
                {
                    'setup_requires' : ['patch_motion'],
                    'advanced' : False,
                    'key' : 'patch_ctf_est', 
                    'job_type' : 'patch_ctf_estimation_multi', 
                    'job_title' : 'Patch CTF Estimation', 
                    'params' : {
                        'do_plots' : False
                    },
                    'input_group_connects' : {
                        'exposures': [
                            {
                                'input_job_name' : 'patch_motion',
                                'group_name' : 'micrographs'
                            }
                        ]
                    }
                }
            ],
            10025 : [
                {
                    'setup_requires' : [],
                    'advanced' : False,
                    'key' : 'import_movies', 
                    'job_type' : 'import_movies', 
                    'job_title' : 'Import Movies', 
                    'params' : {
                        'blob_paths': os.path.join(input_data_dir, 'data/14sep05c_raw_196/*.frames.mrc'),
                        'gainref_path': os.path.join(input_data_dir, 'data/14sep05c_raw_196/norm-amibox05-0.mrc'),
                        'gainref_flip_y' : True,
                        'psize_A' : 0.6575,
                        'accel_kv' : 300,
                        'cs_mm' : 2.7,
                        'total_dose_e_per_A2' : 53
                    },
                    'timeout' : 1800
                },
                {
                    'setup_requires' : ['import_movies'],
                    'advanced' : False,
                    'key' : 'patch_motion', 
                    'job_type' : 'patch_motion_correction_multi', 
                    'job_title' : 'Patch Motion Correction',
                    'params' : {
                        'do_plots' : False
                    },
                    'input_group_connects' : {
                        'movies': [
                            {
                                'input_job_name' : 'import_movies',
                                'group_name': 'imported_movies'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['patch_motion'],
                    'advanced' : False,
                    'key' : 'patch_ctf_est', 
                    'job_type' : 'patch_ctf_estimation_multi', 
                    'job_title' : 'Patch CTF Estimation',
                    'params' : {
                        'do_plots' : False
                    },
                    'input_group_connects' : {
                        'exposures': [
                            {
                                'input_job_name' : 'patch_motion',
                                'group_name' : 'micrographs'
                            }
                        ]
                    }
                },
                {

                }
            ]
        },
        'reconstruct' : {
            10028 : [
                {
                    'setup_requires' : [],
                    'advanced' : False,
                    'key' : 'import_volumes', 
                    'job_type' : 'import_volumes', 
                    'job_title' : 'Import Volume',
                    'params' : {
                        'volume_blob_path' : os.path.join(input_data_dir, 'data/Volumes/cryosparc_P5_J286_class_00_final_volume.mrc')
                    },
                    'timeout' : 1800
                },
                {
                    'setup_requires' : [],
                    'advanced' : False,
                    'key' : 'import_particles', 
                    'job_type' : 'import_particles', 
                    'job_title' : 'Import Particles',
                    'params' : {
                        'particle_meta_path' : os.path.join(input_data_dir, 'data/Particles/shiny_2sets.star'), 
                        'particle_blob_path' : os.path.join(input_data_dir, 'data/Particles'), 
                    },
                    'timeout' : 1800
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'class_2D_050', 
                    'job_type' : 'class_2D', 
                    'job_title' : '2D Classification- 50 Classes',
                    'params' : {
                        'compute_use_ssd' : False,
                        'class2D_K' : 50,
                        'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'class_2D_100', 
                    'job_type' : 'class_2D', 
                    'job_title' : '2D Classification- 100 Classes',
                    'params' : {
                        'compute_use_ssd' : False,
                        'class2D_K' : 100,
                        'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'class_2D_200', 
                    'job_type' : 'class_2D', 
                    'job_title' : '2D Classification- 200 Classes',
                    'params' : {
                        'compute_use_ssd' : False,
                        'class2D_K' : 200,
                        'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'homo_abinit_1', 
                    'job_type' : 'homo_abinit', 
                    'job_title' : 'Ab-Initio- 1 Class',
                    'params' : {
                            'compute_use_ssd' : False,
                            'abinit_K' : 1,
                            'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'homo_abinit_3', 
                    'job_type' : 'homo_abinit', 
                    'job_title' : 'Ab-Initio- 3 Class',
                    'params' : {
                            'compute_use_ssd' : False,
                            'abinit_K' : 3,
                            'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'hetero_refine_3', 
                    'job_type' : 'hetero_refine', 
                    'job_title' : 'Heterogenous Refinement- 3 Class',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' :  [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'hetero_refine_6', 
                    'job_type' : 'hetero_refine', 
                    'job_title' : 'Heterogenous Refinement- 6 Class',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' :  [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            },
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'homo_refine', 
                    'job_type' : 'homo_refine', 
                    'job_title' : 'Homogeneous Refinement (Engine v2)',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' : [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : False,
                    'key' : 'homo_refine_new', 
                    'job_type' : 'homo_refine_new', 
                    'job_title' : 'New Homogeneous Refinement (Engine v3)',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' : [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'homo_refine_sym_6', 
                    'job_type' : 'homo_refine', 
                    'job_title' : 'Homogeneous Refinement C6 Symmetry Enforced (Engine v2)',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0,
                            'refine_symmetry' : 'C6',
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' : [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : False,
                    'key' : 'homo_refine_new_sym_6', 
                    'job_type' : 'homo_refine_new', 
                    'job_title' : 'New Homogeneous Refinement C6 Symmetry Enforced (Engine v3)',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0,
                            'refine_symmetry' : 'C6',
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' : [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'nonuniform_refine', 
                    'job_type' : 'nonuniform_refine', 
                    'job_title' : 'Non-Uniform Refinement',
                    'params' : {
                            'compute_use_ssd' : False,
                            'random_seed' : 0,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'import_particles',
                                'group_name' : 'imported_particles'
                            }
                        ],
                        'volume' : [
                            {
                                'input_job_name' : 'import_volumes',
                                'group_name' : 'imported_volume_1'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'var_3D_3', 
                    'job_type' : 'var_3D', 
                    'job_title' : '3 Mode 3D Variability',
                    'params' : {
                        'compute_use_ssd' : False,
                        'var_filter_res' : 8,
                        'var_K' : 3,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'homo_refine',
                                'group_name' : 'particles'
                            }
                        ],
                        'mask' :  [
                            {
                                'input_job_name' : 'homo_refine',
                                'group_name' : 'mask'
                            }
                        ]
                    }
                },
                {
                    'setup_requires' : ['import_particles', 'import_volumes'],
                    'advanced' : True,
                    'key' : 'var_3D_6', 
                    'job_type' : 'var_3D', 
                    'job_title' : '6 Mode 3D Variability',
                    'params' : {
                            'compute_use_ssd' : False,
                            'var_filter_res' : 8,
                            'var_K' : 6,
                    },
                    'input_group_connects' : {
                        'particles' : [
                            {
                                'input_job_name' : 'homo_refine',
                                'group_name' : 'particles'
                            }
                        ],
                        'mask' :  [
                            {
                                'input_job_name' : 'homo_refine',
                                'group_name' : 'mask'
                            }
                        ]
                    }
                }
            ]
        }
    }

    if job_types_only:
        job_types = []
        for mode, datasets in iter(benchmark_jobs.items()):
            for dataset in datasets:
                if dataset == dataset_selected:
                    for job in benchmark_jobs[mode][dataset]:
                        job_types.append(job['key'])
        return job_types
    if datasets_only:
        datasets_available = []
        for mode, datasets in iter(benchmark_jobs.items()):
            datasets_available.extend(datasets.keys())
        return datasets_available
    if modes_only:
        modes_available = []
        for mode, datasets in iter(benchmark_jobs.items()):
            for dataset in datasets:
                if dataset == dataset_selected:
                    modes_available.append(mode)
        return benchmark_jobs.keys()

    return benchmark_jobs


def get_job_info(benchmark_jobs_dict, dataset_selected, job_key):
    for mode, datasets in iter(benchmark_jobs_dict.items()):
        for dataset in datasets:
            if dataset == dataset_selected:
                for job in benchmark_jobs_dict[mode][dataset]:
                    if job['key'] == job_key:
                        return job


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: 
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def connect_and_get_version(master_hostname, command_core_port):
    global cli
    global db
    print (" Attempting to connect to {}:{}...".format(master_hostname, command_core_port))
    rc.connect(master_hostname, command_core_port)
    cli = rc.cli
    db = rc.db
    print (" Connected to master.")
    sysinfo = cli.get_system_info()
    version = sysinfo['version']
    print (" cryoSPARC version {}".format(version))
    print ("-----------------------------------------------------------------------")
    return version


def benchmark_cryoSPARC(master_hostname, worker_hostname, command_core_port, gpu_devidxs, mode, dataset, project_uid, user_email, output_timings_dir, advanced_mode, job):
    juids = OrderedDict()
    timings = {}

    def queue_and_run_job(key, job_type, job_title = None, params = {}, input_group_connects = {}, timeout = 36000):

        print ("  Running {} ({}) with {} second timeout: ".format(key, job_type, timeout))

        major_version_num = int(version.split('.')[1]) if version != 'develop' else 999
        top_version_num = int(version.split('.')[0][1:]) if version != 'develop' else 999

        make_job_args = {
            'job_type' : job_type, 
            'project_uid' : project_uid, 
            'workspace_uid' : workspace_uid, 
            'user_id' : bench_uuid, 
            'title' : job_title, 
            'params' : params, 
            'input_group_connects' : input_group_connects
        }

        if top_version_num <= 2 and major_version_num < 14:
           # cli.make_job() in cryoSPARC versions prior to v2.14.0 didn't have the "title" argument
           del make_job_args['title']

        juids[key] = cli.make_job(**make_job_args)

        if "import" in job_type:
            cli.update_job(project_uid, juids[key], {'run_on_master_direct' : False, 'errors_build_params' : {}})

        enqueue_job_args = {
            'project_uid' : project_uid,
            'job_uid' : juids[key], 
            'hostname' : worker_hostname, 
            'gpus' : gpu_devidxs
        }

        if top_version_num <= 2 and major_version_num < 14:
            # cli.enqueue_job() in cryoSPARC versions prior to v2.12.0 didn't have the "hostname" or "gpus" arguments, only "lane"
            del enqueue_job_args['hostname']
            del enqueue_job_args['gpus']
            targets = cli.get_scheduler_targets()
            target = rc.com.query(targets, lambda t : t['hostname'] == worker_hostname)
            enqueue_job_args['lane'] = target['lane']
            resources_needed = cli.get_job(project_uid, juids[key], 'resources_needed')['resources_needed']
            resources_needed['slots']['GPU'] = gpu_devidxs
            cli.update_job(project_uid, juids[key], {'resources_needed' : resources_needed})

        time.sleep(0.3)
        cli.enqueue_job(**enqueue_job_args)
        
        jstatus = rc.wait_job_status(project_uid, juids[key], ['completed'], timeout=timeout)
        assert jstatus == 'completed', "{} Job did not finish within {} seconds!".format(job_type, timeout)
            
        #write out text streamlog events to file within the output directory
        all_text_events = list(db.events.find({'project_uid':project_uid, 'job_uid':juids[key], 'type':'text'}, {'_id':0, 'created_at':1, 'text':1}))
        streamlog_path_abs = os.path.join(streamlog_path_rel, '{}-{}_{}_streamlog.log'.format(key, project_uid, juids[key]))
        with open(streamlog_path_abs, 'w') as openfile:
            for event in all_text_events:
                openfile.write("%s  %s\n"%(str(event['created_at']), event['text'].strip('\n')))

        jobt = db.jobs.find_one({'project_uid':project_uid,'uid':juids[key]},{'started_at':1, 'completed_at':1})
        jobtime = (jobt['completed_at'] - jobt['started_at']).total_seconds()
        timings[key] = jobtime
        print ("    Job runtime: %.2f seconds" % jobtime)


    def write_timings_and_disconnect():
        timings_path_abs = os.path.join(streamlog_path_rel,'{}_{}_benchmark_timings.json'.format(project_uid, workspace_uid))
        with open (timings_path_abs, 'w') as f:
            json.dump({'version' : version, 'project_uid':project_uid, 'job_uids' : juids, 'timings' : timings}, f)

        rc.disconnect()


    version = connect_and_get_version(master_hostname, command_core_port)

    if user_email is None:
        user_email = 'Benchmark'
    bench_uuid = cli.get_id_by_email (user_email)
    workspace_uid = cli.create_empty_workspace(
        project_uid=project_uid, 
        created_by_user_id=bench_uuid, 
        title='EMPIAR %d -%s%s Benchmark on %s at %s' % (dataset, " Advanced " if advanced_mode else " ", mode.title() if mode else job, worker_hostname, datetime.datetime.now())
    )
    print (" Created workspace {} in {}".format(workspace_uid, project_uid))
    print ("-----------------------------------------------------------------------")
    streamlog_path_rel = os.path.join(output_timings_dir,'{}_{}_events'.format(project_uid, workspace_uid))
    mkdir_p(streamlog_path_rel)
    print (" Writing job streamlog contents to folder {}".format(streamlog_path_rel))
    print ("-----------------------------------------------------------------------")
    print (" BENCHMARK START")
    print ("-----------------------------------------------------------------------")

    benchmark_jobs = get_benchmark_jobs_dict(input_data_dir)

    if job:
        # job only mode
        def run_single_job(job_info):
            if len(job_info['setup_requires']) == 0:
                input_group_connects = defaultdict(list)
                unconstructed_input_group_connects = job_info.get('input_group_connects', False)
                if unconstructed_input_group_connects:
                    for k,v in iter(unconstructed_input_group_connects.items()):
                        for val in v:
                            input_group_connects[k].append('{}.{}'.format(juids[val['input_job_name']], val['group_name']))

                queue_and_run_job(
                    key = job_info['key'],
                    job_type = job_info['job_type'],
                    job_title = job_info['job_title'],
                    params = job_info.get('params', {}),
                    input_group_connects = input_group_connects,
                    timeout = job_info.get('timeout', 36000),
                )
            else:
                while len(job_info['setup_requires']):
                    job_key = job_info['setup_requires'].pop(0)
                    new_job_info = get_job_info(benchmark_jobs, dataset, job_key)
                    run_single_job(new_job_info)
                run_single_job(job_info)
                
        job_info = get_job_info(benchmark_jobs, dataset, job)
        run_single_job(job_info)

    else:
        for job in benchmark_jobs[mode][dataset]:
            if not advanced_mode and job['advanced']:
                continue

            input_group_connects = defaultdict(list)
            unconstructed_input_group_connects = job.get('input_group_connects', False)
            if unconstructed_input_group_connects:
                for k,v in iter(unconstructed_input_group_connects.items()):
                    for val in v:
                        input_group_connects[k].append('{}.{}'.format(juids[val['input_job_name']], val['group_name']))

            queue_and_run_job(
                key = job['key'],
                job_type = job['job_type'],
                job_title = job['job_title'],
                params = job.get('params', {}),
                input_group_connects = input_group_connects,
                timeout = job.get('timeout', 36000),
            )

    write_timings_and_disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='cryoSPARC Benchmark Tool')
    parser.add_argument('--master_hostname')
    parser.add_argument('--port', type=int)
    parser.add_argument('--worker_hostname')
    parser.add_argument('--gpus')
    parser.add_argument('--input_data_dir')
    parser.add_argument('--project_uid') # project must already exist
    parser.add_argument('--mode')
    parser.add_argument("--advanced", default=False, action="store_true")
    parser.add_argument('--dataset', type=int)
    parser.add_argument('--out')
    parser.add_argument('--job')
    parser.add_argument('--user_email')

    args = parser.parse_args()
    master_hostname = args.master_hostname
    worker_hostname = args.worker_hostname
    base_port = args.port if args.port is not None else 39000
    assert master_hostname is not None, "--master_hostname is required"
    assert worker_hostname is not None, "--worker_hostname is required"
    command_core_port = base_port + 2
    gpu_devidxs = [int(v) for v in args.gpus.split(',')]
    user_email = args.user_email

    print ("-----------------------------------------------------------------------")
    print ("cryoSPARC Benchmark Tool")
    print ("-----------------------------------------------------------------------")
    print (" master: ", master_hostname)
    print (" port  : ", base_port)
    print (" worker: ", worker_hostname)
    print ("-----------------------------------------------------------------------")
    print (" Dataset: ")
    datasets_available = get_benchmark_jobs_dict(datasets_only=True)
    dataset = args.dataset
    assert dataset in datasets_available, "please specify a valid EMPIAR dataset out of the ones available: {}".format(datasets_available)
    print ("  EMPIAR {}".format(dataset))
    print ("-----------------------------------------------------------------------")
    job = args.job if args.job is not None else False
    mode = args.mode if args.mode is not None else False
    advanced_mode = args.advanced
    if job:
        jobs_available = get_benchmark_jobs_dict(job_types_only=True, dataset_selected=dataset)
        assert job in jobs_available, "jobs available for this dataset: {}".format(jobs_available)
        print (" Selected job: {}".format(job))
    elif mode:
        modes_available = get_benchmark_jobs_dict(modes_only=True, dataset_selected=dataset)
        assert mode in modes_available, "modes available for this dataset: {}".format(modes_available)
        print ("  {} benchmark".format(mode.title()))
        print ("-----------------------------------------------------------------------")
        print (" Advanced mode: {}".format(advanced_mode))
        if advanced_mode:
            print (" Running all jobs using {} dataset in {} mode".format(dataset, mode))
    print ("-----------------------------------------------------------------------")
    print (" Will run jobs on GPU(s) : ", gpu_devidxs)
    print ("-----------------------------------------------------------------------")
    print (" Input data will be read from: %s " % args.input_data_dir)
    input_data_dir = args.input_data_dir
    print ("-----------------------------------------------------------------------")
    print (" Intermediate and output data will be stored in project: %s " % args.project_uid)
    project_uid = args.project_uid
    print ("-----------------------------------------------------------------------")
    print (" Timings and job streamlogs will be written to: %s " % args.out)
    output_timings_dir = args.out
    print ("-----------------------------------------------------------------------")

    benchmark_cryoSPARC(master_hostname, worker_hostname, command_core_port, gpu_devidxs, mode, dataset, project_uid, user_email, output_timings_dir, advanced_mode, job)
